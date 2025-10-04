"""Main CLI class for DeepSeek"""

import json
import argparse
from typing import Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich import box
from rich.align import Align
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.text import Text
from pyfiglet import Figlet

console = Console()

try:
    import readline  # noqa
except ImportError:
    pass

# Simplified import handling with clear fallback chain
try:
    from deepseek_cli.api.client import APIClient
    from deepseek_cli.handlers.chat_handler import ChatHandler
    from deepseek_cli.handlers.command_handler import CommandHandler
    from deepseek_cli.handlers.error_handler import ErrorHandler
except ImportError:
    from src.api.client import APIClient
    from src.handlers.chat_handler import ChatHandler
    from src.handlers.command_handler import CommandHandler
    from src.handlers.error_handler import ErrorHandler


    

class DeepSeekCLI:
    def __init__(self, *, stream: bool = False) -> None:
        self.api_client = APIClient()
        self.chat_handler = ChatHandler(stream=stream)
        self.command_handler = CommandHandler(self.api_client, self.chat_handler)
        self.error_handler = ErrorHandler()

    def get_completion(self, user_input: str, raw: bool = False) -> Optional[str]:
        """Get completion from the API with retry logic"""
        try:
            # Add user message to history
            self.chat_handler.add_message("user", user_input)

            # Set raw mode in chat handler
            original_raw_mode = getattr(self.chat_handler, 'raw_mode', False)
            self.chat_handler.raw_mode = raw

            # Prepare request parameters
            kwargs = self.chat_handler.prepare_chat_request()

            def make_request():
                response = self.api_client.create_chat_completion(**kwargs)
                return self.chat_handler.handle_response(response)

            # Execute request with retry logic
            response = self.error_handler.retry_with_backoff(make_request, self.api_client)
            
            # Restore original raw mode
            self.chat_handler.raw_mode = original_raw_mode
            
            return response

        except (KeyError, ValueError, TypeError) as e:
            console.print(f"[red]Error processing request: {str(e)}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Unexpected error: {str(e)}[/red]")
            return None

    def run(self) -> None:
        """Run the CLI interface"""
        # Set initial system message
        self.chat_handler.set_system_message("You are a helpful assistant.")

        self._print_welcome()

        while True:
            # Prompt user input with a styled label
            user_input = Prompt.ask("[bold bright_magenta]> You[/bold bright_magenta]").strip()
            # Handle commands
            result = self.command_handler.handle_command(user_input)
            
            if result[0] is False:  # Exit
                console.print(f"\n{result[1]}")
                break
            elif result[0] is True:  # Command handled
                if result[1]:
                    console.print(f"\n{result[1]}")
                continue

            # Get and handle response
            assistant_response = self.get_completion(user_input)
            if assistant_response:
                if self.chat_handler.json_mode and not self.chat_handler.stream:
                    try:
                        # Pretty print JSON response
                        parsed = json.loads(assistant_response)
                        console.print("\n[bold cyan]Assistant:[/bold cyan]", json.dumps(parsed, indent=2))
                    except json.JSONDecodeError:
                        console.print("\n[bold cyan]Assistant:[/bold cyan]", assistant_response)
                elif not self.chat_handler.stream:
                    # print("\nAssistant:", assistant_response)
                    pass

    def run_inline_query(self, query: str, model: Optional[str] = None, raw: bool = False) -> str:
        """Run a single query and return the response"""
        # Set initial system message
        self.chat_handler.set_system_message("You are a helpful assistant.")

        # Set model if specified
        if model and model in ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]:
            self.chat_handler.switch_model(model)

        # Get and return response
        return self.get_completion(query, raw=raw) or "Error: Failed to get response"
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
    parser.add_argument("-q", "--query", type=str, help="Run in inline mode with the specified query")
    parser.add_argument("-m", "--model", type=str, choices=["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
                        help="Specify the model to use (deepseek-chat, deepseek-coder, deepseek-reasoner)")
    parser.add_argument("-r", "--raw", action="store_true", help="Output raw response without token usage information")
    parser.add_argument("-s", "--stream", action="store_true", help="Enable stream mode")
    return parser.parse_args()

def main() -> None:
    args = parse_arguments()
    cli = DeepSeekCLI(stream=args.stream)

    # Check if running in inline mode
    if args.query:
        # Run in inline mode
        response = cli.run_inline_query(args.query, args.model, args.raw)
        print(response)
    else:
        # Run in interactive mode
        cli.run()

if __name__ == "__main__":
    main()
