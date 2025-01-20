"""Main CLI class for DeepSeek"""

import json
from typing import Optional, Dict, Any, Tuple
from api.client import APIClient
from handlers.chat_handler import ChatHandler
from handlers.command_handler import CommandHandler
from handlers.error_handler import ErrorHandler

class DeepSeekCLI:
    def __init__(self):
        self.api_client = APIClient()
        self.chat_handler = ChatHandler()
        self.command_handler = CommandHandler(self.api_client, self.chat_handler)
        self.error_handler = ErrorHandler()

    def display_token_info(self, usage: dict) -> None:
        """Display token usage information"""
        if usage:
            print("\nToken Usage:")
            print(f"  Input tokens: {usage.get('prompt_tokens', 0)}")
            print(f"  Output tokens: {usage.get('completion_tokens', 0)}")
            print(f"  Total tokens: {usage.get('total_tokens', 0)}")
            
            # Estimate character counts (rough approximation)
            eng_chars = usage.get('total_tokens', 0) * 3  # 1 token ≈ 0.3 English chars
            cn_chars = usage.get('total_tokens', 0) * 1.67  # 1 token ≈ 0.6 Chinese chars
            print("\nEstimated character equivalents:")
            print(f"  English: ~{eng_chars} characters")
            print(f"  Chinese: ~{cn_chars} characters")

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

    def get_completion(self, user_input: str) -> Optional[str]:
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
                    if not self.chat_handler.stream:
                        self.display_token_info(response.usage.model_dump())
                    
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

def main():
    cli = DeepSeekCLI()
    cli.run()

if __name__ == "__main__":
    main() 