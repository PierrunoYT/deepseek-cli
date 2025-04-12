"""Main CLI class for DeepSeek"""

import json
import argparse
from typing import Optional

# Add proper import paths for both development and installed modes
try:
    # When running as an installed package
    from api.client import APIClient
    from handlers.chat_handler import ChatHandler
    from handlers.command_handler import CommandHandler
    from handlers.error_handler import ErrorHandler
except ImportError:
    # When running in development mode
    from src.api.client import APIClient
    from src.handlers.chat_handler import ChatHandler
    from src.handlers.command_handler import CommandHandler
    from src.handlers.error_handler import ErrorHandler

class DeepSeekCLI:
    def __init__(self):
        self.api_client = APIClient()
        self.chat_handler = ChatHandler()
        self.command_handler = CommandHandler(self.api_client, self.chat_handler)
        self.error_handler = ErrorHandler()

    # Token usage display moved to ChatHandler class

    def stream_response(self, response) -> str:
        """Handle streaming response"""
        full_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                print(content, end='', flush=True)
                full_response += content
        print()  # New line after streaming
        return full_response

    def get_completion(self, user_input: str, raw: bool = False) -> Optional[str]:
        """Get completion from the API with retry logic"""
        try:
            # Add user message to history
            self.chat_handler.add_message("user", user_input)

            # Prepare request parameters
            kwargs = self.chat_handler.prepare_chat_request()

            def make_request():
                response = self.api_client.create_chat_completion(**kwargs)
                if self.chat_handler.stream:
                    return self.stream_response(response)
                else:
                    if not self.chat_handler.stream and not raw:
                        self.chat_handler.display_token_info(response.usage.model_dump())

                    # Get the message content
                    message = response.choices[0].message

                    # Check for tool calls (function calling) if they exist
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        return json.dumps([{
                            "id": tool_call.id,
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        } for tool_call in message.tool_calls], indent=2)

                    return message.content

            # Execute request with retry logic
            response = self.error_handler.retry_with_backoff(make_request, self.api_client)

            # Add assistant response to history if successful
            if response:
                self.chat_handler.add_message("assistant", response)

            return response

        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            return None

    def run(self):
        """Run the CLI interface"""
        # Set initial system message
        self.chat_handler.set_system_message("You are a helpful assistant.")

        print("Welcome to DeepSeek CLI! (Type '/help' for commands)")
        print("-" * 50)

        while True:
            user_input = input("\nYou: ").strip()

            # Handle commands
            result = self.command_handler.handle_command(user_input)
            if result[0] is False:  # Exit
                print(f"\n{result[1]}")
                break
            elif result[0] is True:  # Command handled
                if result[1]:
                    print(f"\n{result[1]}")
                continue

            # Get and handle response
            assistant_response = self.get_completion(user_input)
            if assistant_response:
                if self.chat_handler.json_mode and not self.chat_handler.stream:
                    try:
                        # Pretty print JSON response
                        parsed = json.loads(assistant_response)
                        print("\nAssistant:", json.dumps(parsed, indent=2))
                    except json.JSONDecodeError:
                        print("\nAssistant:", assistant_response)
                elif not self.chat_handler.stream:
                    print("\nAssistant:", assistant_response)

    def run_inline_query(self, query: str, model: Optional[str] = None, raw: bool = False) -> str:
        """Run a single query and return the response"""
        # Set initial system message
        self.chat_handler.set_system_message("You are a helpful assistant.")

        # Set model if specified
        if model and model in ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]:
            self.chat_handler.switch_model(model)

        # Get and return response
        return self.get_completion(query, raw=raw) or "Error: Failed to get response"

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="DeepSeek CLI - A powerful command-line interface for DeepSeek's AI models")
    parser.add_argument("-q", "--query", type=str, help="Run in inline mode with the specified query")
    parser.add_argument("-m", "--model", type=str, choices=["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
                        help="Specify the model to use (deepseek-chat, deepseek-coder, deepseek-reasoner)")
    parser.add_argument("-r", "--raw", action="store_true", help="Output raw response without token usage information")
    return parser.parse_args()

def main():
    args = parse_arguments()
    cli = DeepSeekCLI()

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