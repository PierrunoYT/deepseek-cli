"""Main CLI class for DeepSeek"""

import argparse
import atexit
import signal
import sys
from typing import Optional, Tuple
import os
from rich.console import Console
from rich.panel import Panel
from rich import box
from rich.align import Align
from rich.markdown import Markdown
from rich.text import Text

try:
    from pyfiglet import Figlet
except ImportError:
    # Only used by the optional 'fancy' banner; the CLI must import and run
    # without it (the test suite imports this module directly).
    Figlet = None

console = Console()

DEFAULT_SYSTEM_MESSAGE = "You are a helpful assistant."

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
except ImportError:
    PromptSession = None
    KeyBindings = None

try:
    import readline  # noqa
except ImportError:
    pass


def multiline_input(prompt: str, submit_mode: str = "shift-enter") -> str:
    """Get multiline input with configurable submit behavior.

    submit_mode:
      - shift-enter: Enter inserts newline, Shift+Enter submits.
      - empty-line: Enter inserts newline, a blank line submits.
    """
    if PromptSession and KeyBindings:
        key_bindings = KeyBindings()

        @key_bindings.add("enter")
        def _(event):
            if (
                submit_mode == "empty-line"
                and event.current_buffer.document.current_line.strip() == ""
            ):
                event.current_buffer.validate_and_handle()
            else:
                event.current_buffer.insert_text("\n")

        @key_bindings.add("c-d")
        def _(event):
            event.current_buffer.validate_and_handle()

        if submit_mode == "shift-enter":

            @key_bindings.add("s-enter")
            def _(event):
                event.current_buffer.validate_and_handle()

        session = PromptSession(multiline=True, key_bindings=key_bindings)
        try:
            return session.prompt(f"{prompt}: ")
        except KeyboardInterrupt:
            console.print("\n[yellow]Input cancelled[/yellow]")
            return ""
        except EOFError:
            return ""

    lines = []
    fallback_help = "Enter for newline, Ctrl+D or empty line to submit"
    if submit_mode == "shift-enter":
        fallback_help += " (Shift+Enter requires prompt_toolkit)"

    console.print(f"{prompt} [dim]({fallback_help})[/dim]")

    try:
        while True:
            try:
                line = input()
                if not line:
                    break
                lines.append(line)
                console.print("... ", end="")
            except EOFError:
                break
    except KeyboardInterrupt:
        console.print("\n[yellow]Input cancelled[/yellow]")
        return ""

    return "\n".join(lines)


from deepseek_cli.api.client import APIClient
from deepseek_cli.handlers.chat_handler import ChatHandler
from deepseek_cli.handlers.command_handler import CommandHandler
from deepseek_cli.handlers.error_handler import ErrorHandler
from deepseek_cli.handlers.file_handler import FileHandler
from deepseek_cli.utils.exceptions import DeepSeekError
from deepseek_cli.config.settings import (
    MODEL_CONFIGS,
    LEGACY_MODEL_ALIASES,
    REASONING_EFFORT_LEVELS,
)


class DeepSeekCLI:
    def __init__(
        self,
        *,
        stream: bool = False,
        multiline: bool = False,
        multiline_submit: str = "empty-line",
    ) -> None:
        self.api_client = APIClient()
        self.chat_handler = ChatHandler(stream=stream)
        self.file_handler = FileHandler()
        self.command_handler = CommandHandler(
            self.api_client, self.chat_handler, self.file_handler
        )
        self.error_handler = ErrorHandler()
        self.multiline = multiline
        self.multiline_submit = multiline_submit

        # Register cleanup handlers. SIGINT is deliberately left at Python's
        # default (raise KeyboardInterrupt) so Ctrl+C cancels the current
        # input line instead of tearing down the whole session; the REPL loop
        # handles it. Overriding it also made the loop's KeyboardInterrupt
        # handler unreachable.
        atexit.register(self._cleanup)
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (ValueError, AttributeError, OSError):
            # Not the main thread, or SIGTERM unavailable on this platform.
            pass

    def _ensure_beta_for_beta_features(self) -> None:
        """Switch to the Beta host when a Beta-only feature is active.

        Prefix completion and FIM are documented as requiring
        base_url=https://api.deepseek.com/beta. Enabling them without it fails
        server-side, so turn beta on rather than letting the request 400.
        """
        needs_beta = self.chat_handler.prefix_mode or self.chat_handler.fim_mode
        if needs_beta and not self.api_client.beta_mode:
            feature = "FIM" if self.chat_handler.fim_mode else "Prefix completion"
            self.api_client.toggle_beta()
            console.print(
                f"[cyan]{feature} requires the beta endpoint; enabling beta mode "
                f"for this session (toggle with /beta).[/cyan]"
            )

    def _has_system_message(self) -> bool:
        """True when the loaded conversation already starts with a system message."""
        messages = self.chat_handler.messages
        return bool(messages) and messages[0].get("role") == "system"

    def _cleanup(self) -> None:
        """Cleanup function called on exit"""
        try:
            self.chat_handler.save_state()
        except Exception:
            pass  # Silently fail during cleanup

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals"""
        console.print("\n[yellow]Saving session data...[/yellow]")
        self._cleanup()
        sys.exit(0)

    def get_completion(self, user_input: str, raw: bool = False) -> Optional[str]:
        """Get completion from the API with retry logic"""
        try:
            # If files are attached, fold their contents into the user message
            # and clear the attachment list (one-shot, matches DeepSeek app UX).
            if self.file_handler.has_attachments():
                attached_paths = [
                    f["path"] for f in self.file_handler.list_attachments()
                ]
                console.print(
                    f"[cyan]Including {len(attached_paths)} attached file(s) "
                    f"with this message.[/cyan]"
                )
                user_input = self.file_handler.format_for_message(user_input)
                self.file_handler.clear()

            # Prefix completion and FIM are Beta-only features; without the
            # beta host the API rejects them, so switch over automatically.
            self._ensure_beta_for_beta_features()

            fim = self.chat_handler.fim_mode
            if not fim:
                # FIM is a text completion, not a conversation turn, so it is
                # deliberately kept out of the chat history.
                self.chat_handler.add_message("user", user_input)

            original_raw_mode = self.chat_handler.raw_mode
            self.chat_handler.raw_mode = raw

            def make_request():
                # Rebuild kwargs on every attempt so prefix-mode and any
                # state changes (e.g. new API key after 401 recovery) apply.
                if fim:
                    prefix, suffix = self.chat_handler.parse_fim_input(user_input)
                    kwargs = self.chat_handler.prepare_fim_request(prefix, suffix)
                    response = self.api_client.create_completion(**kwargs)
                    return self.chat_handler.handle_completion_response(response)
                kwargs = self.chat_handler.prepare_chat_request()
                response = self.api_client.create_chat_completion(**kwargs)
                return self.chat_handler.handle_response(response)

            try:
                return self.error_handler.retry_with_backoff(
                    make_request, self.api_client
                )
            finally:
                # Restore unconditionally; an exception here used to leave
                # raw_mode stuck for the rest of the session.
                self.chat_handler.raw_mode = original_raw_mode

        except (KeyError, ValueError, TypeError) as e:
            console.print(f"[red]Error processing request: {str(e)}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Unexpected error: {str(e)}[/red]")
            return None

    def run(self, system_message: Optional[str] = None) -> None:
        """Run the CLI interface.

        Args:
            system_message: Explicit system message from --system. When None,
                a system message persisted from a previous session (set via
                /system) is preserved; previously it was silently overwritten
                with the default on every start.
        """
        if system_message is not None:
            self.chat_handler.set_system_message(system_message)
        elif not self._has_system_message():
            self.chat_handler.set_system_message(DEFAULT_SYSTEM_MESSAGE)

        self._print_welcome()

        # Show multiline mode status if enabled
        if self.multiline:
            if self.multiline_submit == "shift-enter":
                console.print(
                    "[cyan]Multiline mode enabled: Enter for newlines, Shift+Enter or Ctrl+D to submit[/cyan]\n"
                )
            else:
                console.print(
                    "[cyan]Multiline mode enabled: Enter for newlines, empty line or Ctrl+D to submit[/cyan]\n"
                )

        # Consecutive Ctrl+C presses with no successful input in between.
        interrupts = 0

        try:
            while True:
                try:
                    # Prompt user input with multiline support if enabled
                    if self.multiline:
                        user_input = multiline_input(
                            "> You", self.multiline_submit
                        ).strip()
                    else:
                        # Use plain input() instead of Prompt.ask() to avoid conflicts with readline
                        console.print(
                            "[bold bright_magenta]> You[/bold bright_magenta]: ", end=""
                        )
                        user_input = input().strip()

                    # A successful read resets the Ctrl+C exit counter.
                    interrupts = 0

                    # Handle empty input (just pressing Enter)
                    if not user_input:
                        continue
                    # Handle commands
                    result = self.command_handler.handle_command(user_input)

                    if result[0] is False:  # Exit
                        console.print(f"\n{result[1]}")
                        break
                    elif result[0] is True:  # Command handled
                        if result[1]:
                            console.print(f"\n{result[1]}")
                        continue

                    # Get and handle response — handle_response already prints the
                    # panel (or streams), so no additional output is needed here.
                    self.get_completion(user_input)

                except EOFError:
                    # Ctrl+D pressed - exit gracefully
                    console.print("\n[yellow]Exiting...[/yellow]")
                    break
                except KeyboardInterrupt:
                    # First Ctrl+C cancels the current line; a second one with
                    # nothing entered in between exits. Cancelling the line is
                    # the useful behaviour, and the two-strike rule guarantees
                    # the loop still terminates when stdin can only interrupt.
                    interrupts += 1
                    if interrupts >= 2:
                        console.print("\n[yellow]Exiting...[/yellow]")
                        break
                    console.print(
                        "\n[yellow]Cancelled. Press Ctrl+C again, Ctrl+D, "
                        "or type /quit to exit.[/yellow]"
                    )
                    continue

        except KeyboardInterrupt:
            # Interrupt outside the input/response cycle - exit gracefully
            console.print("\n[yellow]Exiting...[/yellow]")
        finally:
            # Ensure cleanup happens
            self._cleanup()

    def _apply_cli_args(self, args: argparse.Namespace) -> None:
        """Apply CLI flags to the chat/api state before a session starts.

        Called from main() after DeepSeekCLI is constructed, and before
        run() / run_inline_query() so that the session starts with the
        settings the user requested on the command line.

        Note: json_mode is set directly (not via toggle_json_mode) so that
        the user-supplied --system message is not overwritten.
        """
        if getattr(args, "json", False):
            self.chat_handler.json_mode = True
        if getattr(args, "beta", False):
            self.api_client.toggle_beta()
        if getattr(args, "prefix", False):
            self.chat_handler.prefix_mode = True
        if getattr(args, "fim", False):
            self.chat_handler.fim_mode = True
        if getattr(args, "think", False):
            self.chat_handler.thinking = True
        if getattr(args, "reasoning_effort", None) is not None:
            self.chat_handler.set_reasoning_effort(args.reasoning_effort)
        if getattr(args, "max_tokens", None) is not None:
            if not self.chat_handler.set_max_tokens(args.max_tokens):
                console.print(
                    f"[yellow]! Ignoring --max-tokens {args.max_tokens}: must be "
                    f"between 1 and "
                    f"{MODEL_CONFIGS[self.chat_handler.model]['max_tokens']}.[/yellow]"
                )
        if getattr(args, "temp", None) is not None:
            self.chat_handler.set_temperature(str(args.temp))
        if getattr(args, "freq", None) is not None or getattr(args, "pres", None) is not None:
            console.print(
                "[yellow]! --freq/--pres are ignored: the DeepSeek API no longer "
                "supports frequency_penalty/presence_penalty.[/yellow]"
            )
        if getattr(args, "top_p", None) is not None:
            self.chat_handler.set_top_p(args.top_p)
        if getattr(args, "stop", None):
            for seq in args.stop:
                self.chat_handler.add_stop_sequence(seq)
        if getattr(args, "files", None):
            allow_sensitive = getattr(args, "allow_sensitive", False)
            for pattern in args.files:
                attached, errors = self.file_handler.attach(
                    pattern, allow_sensitive=allow_sensitive
                )
                for p in attached:
                    console.print(f"[green]+ attached:[/green] {p}")
                for e in errors:
                    console.print(f"[yellow]! {e}[/yellow]")

    def run_inline_query(
        self,
        query: str,
        model: Optional[str] = None,
        raw: bool = False,
        system_message: Optional[str] = None,
    ) -> str:
        """Run a single query and return the response"""
        # An explicit --system always wins; otherwise keep any persisted
        # system message and only fall back to the default if there is none.
        if system_message is not None:
            self.chat_handler.set_system_message(system_message)
        elif not self._has_system_message():
            self.chat_handler.set_system_message(DEFAULT_SYSTEM_MESSAGE)

        # Set model if specified (switch_model validates and maps retired names)
        if model and not self.chat_handler.switch_model(model):
            console.print(f"[yellow]! Unknown model '{model}'; keeping "
                          f"{self.chat_handler.model}.[/yellow]")

        # Get and return response
        result = self.get_completion(query, raw=raw) or "Error: Failed to get response"

        # Save state after inline query
        self.chat_handler.save_state()

        return result

    def _print_welcome(self, style: str = "simple") -> None:
        """Display a stylish welcome banner.

        Args:
            style: Banner style - 'simple' for minimal or 'fancy' for ASCII art
        """

        if style != "simple" and Figlet is None:
            # pyfiglet is optional; degrade to the simple banner.
            style = "simple"

        if style == "simple":
            panel = Panel(
                Align.center(
                    "Use natural language to interact with AI.\nType /help for commands, or exit to quit.",
                    vertical="middle",
                ),
                title="💡 DeepSeek CLI",
                border_style="cyan",
                box=box.SIMPLE,
            )
            console.print(panel)
        else:
            fig = Figlet(font="slant")
            ascii_title = fig.renderText("DeepSeek CLI")

            # Apply gradient colors to ASCII art
            gradient_title = Text()
            colors = ["#FF61A6", "#FF82B2", "#FF9DC3", "#C18AFF", "#7A7CFF", "#4BCFFF"]
            for i, line in enumerate(ascii_title.splitlines()):
                gradient_title.append(line + "\n", style=colors[i % len(colors)])

            # Panel for the welcome banner
            welcome_panel = Panel(
                Align.center(gradient_title),
                border_style="bold #FF82B2",
                box=box.ROUNDED,
                padding=(1, 2),
                title="[bold #4BCFFF]🚀 Welcome 🚀[/bold #4BCFFF]",
                subtitle="[italic #7A7CFF]Type 'exit' to quit[/italic #7A7CFF]",
                expand=True,
            )
            console.print(welcome_panel)
            console.print()


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="DeepSeek CLI - A powerful command-line interface for DeepSeek's AI models"
    )

    # Core options
    parser.add_argument(
        "-q", "--query", type=str, help="Run in inline mode with the specified query"
    )
    parser.add_argument(
        "--read",
        type=str,
        default=None,
        metavar="FILE",
        help=(
            "Read query text from FILE, or '-' to read from stdin (pipe). "
            "When combined with -q/--query the file/pipe content is appended "
            "after the query text separated by a newline."
        ),
    )
    parser.add_argument(
        "--file",
        type=str,
        action="append",
        default=None,
        metavar="PATH",
        dest="files",
        help=(
            "Attach a file (or glob pattern) for analysis; the file's text "
            "is folded into the next user message. Repeatable: --file a.py "
            "--file 'src/*.py'. Inside the REPL use /file, /pick, /files, "
            "/clearfiles for the same feature."
        ),
    )
    parser.add_argument(
        "--allow-sensitive",
        action="store_true",
        default=False,
        dest="allow_sensitive",
        help=(
            "Permit --file to attach credential-shaped files (.env, "
            "~/.ssh/id_rsa, *.pem, ~/.aws/credentials ...). These are refused "
            "by default because their contents would be uploaded to the API."
        ),
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        choices=sorted(MODEL_CONFIGS) + sorted(LEGACY_MODEL_ALIASES),
        metavar="MODEL",
        help=(
            "Model to use: " + ", ".join(sorted(MODEL_CONFIGS)) + ". The retired "
            "names (" + ", ".join(sorted(LEGACY_MODEL_ALIASES)) + ") are accepted "
            "and mapped to their replacement with a warning."
        ),
    )
    parser.add_argument(
        "-r",
        "--raw",
        action="store_true",
        help="Output raw response without token usage information",
    )
    parser.add_argument(
        "-S",
        "--system",
        type=str,
        default=None,
        help=(
            "Set the system message. When omitted, a system message saved "
            "from a previous session (via /system) is kept, otherwise "
            f"'{DEFAULT_SYSTEM_MESSAGE}' is used."
        ),
    )

    # Streaming
    parser.add_argument(
        "-s", "--stream", action="store_true", help="Enable streaming mode"
    )
    parser.add_argument(
        "--no-stream",
        dest="stream",
        action="store_false",
        help="Disable streaming mode",
    )

    # Output / mode flags (mirror REPL commands)
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Enable JSON output mode (sets response_format to json_object)",
    )
    parser.add_argument(
        "--beta", action="store_true", default=False, help="Enable beta API endpoint"
    )
    parser.add_argument(
        "--prefix",
        action="store_true",
        default=False,
        help="Enable prefix completion mode (last user message becomes assistant prefix)",
    )
    parser.add_argument(
        "--fim",
        action="store_true",
        default=False,
        help=(
            "Enable Fill-in-the-Middle mode (use <fim_prefix>/<fim_suffix> tags). "
            "Uses the beta completions endpoint; output is capped at 4K tokens."
        ),
    )
    parser.add_argument(
        "--think",
        action="store_true",
        default=False,
        help=(
            "Enable Thinking mode. On the V4 models this is a per-request "
            "parameter, replacing the retired deepseek-reasoner model."
        ),
    )
    parser.add_argument(
        "--reasoning-effort",
        type=str,
        choices=list(REASONING_EFFORT_LEVELS),
        default=None,
        dest="reasoning_effort",
        help="Reasoning effort used when Thinking mode is on (default: high)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        dest="max_tokens",
        metavar="N",
        help="Maximum output tokens for this session (model maximum is 384000)",
    )

    # Input behavior
    parser.add_argument(
        "--multiline",
        action="store_true",
        default=False,
        help="Enable multiline input mode (Enter for newlines, empty line or Ctrl+D to submit by default)",
    )
    parser.add_argument(
        "--multiline-submit",
        type=str,
        choices=["shift-enter", "empty-line"],
        default="empty-line",
        help="Multiline submit mode: empty-line (default) or shift-enter (requires terminal support)",
    )

    # Sampling / penalty parameters (mirror REPL /temp, /freq, /pres, /top_p)
    parser.add_argument(
        "--temp",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Set temperature (0-2, or use REPL presets via /temp inside session)",
    )
    # --freq / --pres are accepted but ignored: the API documents
    # frequency_penalty and presence_penalty as no longer supported. They are
    # kept so existing scripts do not fail on an unrecognised argument.
    parser.add_argument(
        "--freq",
        type=float,
        default=None,
        metavar="FLOAT",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--pres",
        type=float,
        default=None,
        metavar="FLOAT",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=None,
        dest="top_p",
        metavar="FLOAT",
        help="Set top_p sampling (0 to 1)",
    )

    # Stop sequences (repeatable, mirrors /stop)
    parser.add_argument(
        "--stop",
        type=str,
        action="append",
        default=None,
        metavar="SEQ",
        help="Add a stop sequence (can be repeated: --stop A --stop B)",
    )

    return parser.parse_args()


def _read_input(source: str) -> str:
    """Read text from *source*.

    Args:
        source: A file path or ``'-'`` for stdin.

    Returns:
        The contents of the file / stdin as a string.

    Raises:
        SystemExit: When the file cannot be opened or stdin is a TTY (not piped).
    """
    if source == "-":
        if sys.stdin.isatty():
            console.print(
                "[red]Error: --read - requires input to be piped or redirected "
                "(stdin is a terminal).[/red]"
            )
            sys.exit(1)
        return sys.stdin.read()

    try:
        with open(source, "r", encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError as exc:
        console.print(
            f"[red]Error: '{source}' could not be decoded as UTF-8: {exc}[/red]"
        )
        sys.exit(1)
    except OSError as exc:
        console.print(f"[red]Error reading '{source}': {exc}[/red]")
        sys.exit(1)


def main() -> None:
    args = parse_arguments()

    # Resolve the final query text, honouring --read / pipe input.
    query: Optional[str] = args.query
    inline_mode: bool = query is not None

    if args.read is not None:
        read_text = _read_input(args.read)
        inline_mode = True
        if query is not None:
            # Minimal normalization: ensure exactly one newline at the join point
            # without touching the read content itself.
            query = query.rstrip("\n") + "\n" + read_text
        else:
            query = read_text

    try:
        cli = DeepSeekCLI(
            stream=args.stream,
            multiline=args.multiline,
            multiline_submit=args.multiline_submit,
        )
    except DeepSeekError as exc:
        # e.g. no API key and no interactive terminal to prompt on.
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)

    # Apply REPL-equivalent flags (temp, freq, pres, top_p, stop, json, beta, prefix, fim)
    cli._apply_cli_args(args)

    if inline_mode:
        response = cli.run_inline_query(query or "", args.model, args.raw, args.system)
        print(response)
    else:
        cli.run(args.system)


if __name__ == "__main__":
    main()
