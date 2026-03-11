"""Main CLI class for DeepSeek"""

import argparse
import atexit
import signal
import sys
from typing import Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich import box
from rich.align import Align
from rich.markdown import Markdown
from rich.text import Text
from pyfiglet import Figlet

console = Console()

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
            if submit_mode == "empty-line" and event.current_buffer.document.current_line.strip() == "":
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

# Simplified import handling with clear fallback chain
try:
    # When installed via pip/pipx (package_dir={"": "src"})
    from api.client import APIClient
    from handlers.chat_handler import ChatHandler
    from handlers.command_handler import CommandHandler
    from handlers.error_handler import ErrorHandler
except ImportError:
    # When running from source (development mode)
    from src.api.client import APIClient
    from src.handlers.chat_handler import ChatHandler
    from src.handlers.command_handler import CommandHandler
    from src.handlers.error_handler import ErrorHandler


    

class DeepSeekCLI:
    def __init__(self, *, stream: bool = False, multiline: bool = False,
                 multiline_submit: str = "empty-line") -> None:
        self.api_client = APIClient()
        self.chat_handler = ChatHandler(stream=stream)
        self.command_handler = CommandHandler(self.api_client, self.chat_handler)
        self.error_handler = ErrorHandler()
        self.multiline = multiline
        self.multiline_submit = multiline_submit
        
        # Register cleanup handlers
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

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
            # Add user message to history
            self.chat_handler.add_message("user", user_input)

            original_raw_mode = self.chat_handler.raw_mode
            self.chat_handler.raw_mode = raw

            def make_request():
                # Rebuild kwargs on every attempt so prefix-mode and any
                # state changes (e.g. new API key after 401 recovery) apply.
                kwargs = self.chat_handler.prepare_chat_request()
                response = self.api_client.create_chat_completion(**kwargs)
                return self.chat_handler.handle_response(response)

            result = self.error_handler.retry_with_backoff(make_request, self.api_client)

            self.chat_handler.raw_mode = original_raw_mode
            return result

        except (KeyError, ValueError, TypeError) as e:
            console.print(f"[red]Error processing request: {str(e)}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Unexpected error: {str(e)}[/red]")
            return None

    def run(self, system_message: str = "You are a helpful assistant.") -> None:
        """Run the CLI interface"""
        # Set initial system message
        self.chat_handler.set_system_message(system_message)

        self._print_welcome()
        
        # Show multiline mode status if enabled
        if self.multiline:
            if self.multiline_submit == "shift-enter":
                console.print("[cyan]Multiline mode enabled: Enter for newlines, Shift+Enter or Ctrl+D to submit[/cyan]\n")
            else:
                console.print("[cyan]Multiline mode enabled: Enter for newlines, empty line or Ctrl+D to submit[/cyan]\n")

        try:
            while True:
                try:
                    # Prompt user input with multiline support if enabled
                    if self.multiline:
                        user_input = multiline_input("> You", self.multiline_submit).strip()
                    else:
                        # Use plain input() instead of Prompt.ask() to avoid conflicts with readline
                        console.print("[bold bright_magenta]> You[/bold bright_magenta]: ", end="")
                        user_input = input().strip()
                    
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
            # Ctrl+C pressed - exit gracefully
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
        if getattr(args, "temp", None) is not None:
            self.chat_handler.set_temperature(str(args.temp))
        if getattr(args, "freq", None) is not None:
            self.chat_handler.set_frequency_penalty(args.freq)
        if getattr(args, "pres", None) is not None:
            self.chat_handler.set_presence_penalty(args.pres)
        if getattr(args, "top_p", None) is not None:
            self.chat_handler.set_top_p(args.top_p)
        if getattr(args, "stop", None):
            for seq in args.stop:
                self.chat_handler.add_stop_sequence(seq)

    def run_inline_query(self, query: str, model: Optional[str] = None, raw: bool = False,
                          system_message: str = "You are a helpful assistant.") -> str:
        """Run a single query and return the response"""
        # Only set system message if no messages exist (don't override persisted system message)
        if not self.chat_handler.messages:
            self.chat_handler.set_system_message(system_message)

        # Set model if specified
        if model and model in ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]:
            self.chat_handler.switch_model(model)

        # Get and return response
        result = self.get_completion(query, raw=raw) or "Error: Failed to get response"
        
        # Save state after inline query
        self.chat_handler.save_state()
        
        return result
    def _print_welcome(self, style: str = 'simple') -> None:
        """Display a stylish welcome banner.
        
        Args:
            style: Banner style - 'simple' for minimal or 'fancy' for ASCII art
        """

        if style == 'simple':
            panel = Panel(
                Align.center(
                    "Use natural language to interact with AI.\nType /help for commands, or exit to quit.",
                    vertical="middle"
                ),
                title="💡 DeepSeek CLI",
                border_style="cyan",
                box=box.SIMPLE
            )
            console.print(panel)        
        else: 
            fig = Figlet(font='slant')
            ascii_title = fig.renderText('DeepSeek CLI')

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
                expand=True
            )
            console.print(welcome_panel)
            console.print()

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="DeepSeek CLI - A powerful command-line interface for DeepSeek's AI models")

    # Core options
    parser.add_argument("-q", "--query", type=str, help="Run in inline mode with the specified query")
    parser.add_argument("-m", "--model", type=str, choices=["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
                        help="Specify the model to use (deepseek-chat, deepseek-coder, deepseek-reasoner)")
    parser.add_argument("-r", "--raw", action="store_true", help="Output raw response without token usage information")
    parser.add_argument("-S", "--system", type=str, default="You are a helpful assistant.",
                        help="Set the system message (default: 'You are a helpful assistant.')")

    # Streaming
    parser.add_argument("-s", "--stream", action="store_true", help="Enable streaming mode")
    parser.add_argument("--no-stream", dest="stream", action="store_false", help="Disable streaming mode")

    # Output / mode flags (mirror REPL commands)
    parser.add_argument("--json", action="store_true", default=False,
                        help="Enable JSON output mode (sets response_format to json_object)")
    parser.add_argument("--beta", action="store_true", default=False,
                        help="Enable beta API endpoint")
    parser.add_argument("--prefix", action="store_true", default=False,
                        help="Enable prefix completion mode (last user message becomes assistant prefix)")
    parser.add_argument("--fim", action="store_true", default=False,
                        help="Enable Fill-in-the-Middle mode (use <fim_prefix>/<fim_suffix> tags)")
    
    # Input behavior
    parser.add_argument("--multiline", action="store_true", default=False,
                        help="Enable multiline input mode (Enter for newlines, empty line or Ctrl+D to submit by default)")
    parser.add_argument("--multiline-submit", type=str, choices=["shift-enter", "empty-line"], default="empty-line",
                        help="Multiline submit mode: empty-line (default) or shift-enter (requires terminal support)")

    # Sampling / penalty parameters (mirror REPL /temp, /freq, /pres, /top_p)
    parser.add_argument("--temp", type=float, default=None, metavar="FLOAT",
                        help="Set temperature (0-2, or use REPL presets via /temp inside session)")
    parser.add_argument("--freq", type=float, default=None, metavar="FLOAT",
                        help="Set frequency penalty (-2 to 2)")
    parser.add_argument("--pres", type=float, default=None, metavar="FLOAT",
                        help="Set presence penalty (-2 to 2)")
    parser.add_argument("--top-p", type=float, default=None, dest="top_p", metavar="FLOAT",
                        help="Set top_p sampling (0 to 1)")

    # Stop sequences (repeatable, mirrors /stop)
    parser.add_argument("--stop", type=str, action="append", default=None, metavar="SEQ",
                        help="Add a stop sequence (can be repeated: --stop A --stop B)")

    return parser.parse_args()

def main() -> None:
    args = parse_arguments()
    cli = DeepSeekCLI(stream=args.stream, multiline=args.multiline, multiline_submit=args.multiline_submit)

    # Apply REPL-equivalent flags (temp, freq, pres, top_p, stop, json, beta, prefix, fim)
    cli._apply_cli_args(args)

    # Check if running in inline mode
    if args.query:
        # Run in inline mode
        response = cli.run_inline_query(args.query, args.model, args.raw, args.system)
        print(response)
    else:
        # Run in interactive mode
        cli.run(args.system)

if __name__ == "__main__":
    main()
