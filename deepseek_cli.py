import os
import json
import time
from openai import OpenAI
from openai.types.error import APIError, RateLimitError
from typing import Optional, Dict, Any, List
import sys

class DeepSeekError(Exception):
    """Base exception class for DeepSeek CLI errors"""
    pass

class RateLimitExceeded(DeepSeekError):
    """Exception raised when API rate limit is exceeded"""
    pass

class DeepSeekCLI:
    # API Information
    API_CONTACT = "api-service@deepseek.com"
    API_LICENSE = "MIT"
    API_TERMS = "https://platform.deepseek.com/downloads/DeepSeek%20Open%20Platform%20Terms%20of%20Service.html"
    API_AUTH_TYPE = "Bearer"
    API_DOCS = "https://api-docs.deepseek.com/api/create-chat-completion"

    def __init__(self):
        self.beta_mode = False
        self.client = OpenAI(
            api_key=self.get_api_key(),
            base_url="https://api.deepseek.com/v1",  # Updated to v1 endpoint for better OpenAI compatibility
            default_headers={"Authorization": f"Bearer {self.get_api_key()}"}
        )
        self.messages = []
        self.conversation_turn = 0  # Track conversation turns
        self.model = "deepseek-chat"  # Default to DeepSeek-V3
        self.stream = False
        self.json_mode = False
        self.max_tokens = 4096
        self.functions = []
        self.prefix_mode = False
        self.fim_mode = False
        self.context_cache = True  # Enable context caching by default
        self.max_retries = 3
        self.retry_delay = 1  # Initial delay in seconds
        self.max_retry_delay = 16  # Maximum delay in seconds
        self.temperature = 1.0  # Default temperature
        self.frequency_penalty = 0.0  # Default frequency penalty
        self.presence_penalty = 0.0  # Default presence penalty
        self.top_p = 1.0  # Default top_p
        self.stop_sequences = []  # Default stop sequences
        self.stream_options = {"include_usage": True}  # Default stream options
        
        # Model specific configurations
        self.model_configs = {
            "deepseek-chat": {
                "max_tokens": 64000,  # 64K context length
                "max_output": 4096,   # Default output limit
                "beta_max_output": 8192  # Beta output limit
            },
            "deepseek-reasoner": {
                "max_tokens": 64000,  # 64K context length
                "max_output": 8192,   # Output limit
                "cot_output": 32000   # Chain of Thought limit
            },
            "deepseek-coder": {
                "max_tokens": 64000,  # 64K context length
                "max_output": 4096,   # Default output limit
                "beta_max_output": 8192  # Beta output limit
            }
        }
        
        # Use case temperature presets
        self.temperature_presets = {
            "coding": 0.0,
            "data": 1.0,
            "chat": 1.3,
            "translation": 1.3,
            "creative": 1.5
        }

    @staticmethod
    def get_api_key() -> str:
        """Get API key from environment variable or prompt user"""
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            api_key = input("Please enter your DeepSeek API key: ")
        return api_key

    def toggle_beta(self) -> None:
        """Toggle beta features"""
        self.beta_mode = not self.beta_mode
        self.client.base_url = "https://api.deepseek.com/beta" if self.beta_mode else "https://api.deepseek.com/v1"
        print(f"\nBeta mode {'enabled' if self.beta_mode else 'disabled'}")

    def toggle_prefix_mode(self) -> None:
        """Toggle prefix completion mode"""
        if not self.beta_mode:
            print("\nError: Prefix mode requires beta mode. Use /beta first.")
            return
        self.prefix_mode = not self.prefix_mode
        print(f"\nPrefix mode {'enabled' if self.prefix_mode else 'disabled'}")

    def toggle_fim_mode(self) -> None:
        """Toggle Fill-in-the-Middle completion mode"""
        if not self.beta_mode:
            print("\nError: FIM mode requires beta mode. Use /beta first.")
            return
        self.fim_mode = not self.fim_mode
        print(f"\nFIM mode {'enabled' if self.fim_mode else 'disabled'}")
        if self.fim_mode:
            print("Use <fim_prefix>content before gap</fim_prefix><fim_suffix>content after gap</fim_suffix> format")

    def toggle_context_cache(self) -> None:
        """Toggle context caching"""
        self.context_cache = not self.context_cache
        print(f"\nContext caching {'enabled' if self.context_cache else 'disabled'}")

    def set_system_message(self, content: str) -> None:
        """Set or update the system message"""
        if not self.messages or self.messages[0]["role"] != "system":
            self.messages.insert(0, {"role": "system", "content": content})
        else:
            self.messages[0]["content"] = content

    def toggle_json_mode(self) -> None:
        """Toggle JSON output mode"""
        self.json_mode = not self.json_mode
        if self.json_mode:
            self.set_system_message("You are a helpful assistant. Please provide all responses in valid JSON format.")
        else:
            self.set_system_message("You are a helpful assistant.")
        print(f"\nJSON mode {'enabled' if self.json_mode else 'disabled'}")

    def toggle_stream(self) -> None:
        """Toggle streaming mode"""
        self.stream = not self.stream
        print(f"\nStreaming {'enabled' if self.stream else 'disabled'}")

    def switch_model(self, model: str) -> None:
        """Switch between available models"""
        available_models = ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]
        if model in available_models:
            # Check and disable unsupported features for reasoning model
            if model == "deepseek-reasoner":
                if self.json_mode:
                    print("\nWarning: JSON mode is not supported by deepseek-reasoner. Disabling...")
                    self.json_mode = False
                if self.functions:
                    print("\nWarning: Function calling is not supported by deepseek-reasoner. Clearing functions...")
                    self.functions = []
                # Reset unsupported parameters to their defaults
                self.temperature = 1.0
                self.top_p = 1.0
                self.presence_penalty = 0.0
                self.frequency_penalty = 0.0
                print("\nNote: deepseek-reasoner does not support temperature, top_p, presence_penalty, and frequency_penalty.")
            
            self.model = model
            config = self.model_configs[model]
            self.max_tokens = config["max_tokens"]
            max_output = config["beta_max_output"] if self.beta_mode and model != "deepseek-reasoner" else config["max_output"]
            
            print(f"\nSwitched to {model} model")
            print(f"Context length: {self.max_tokens} tokens")
            print(f"Maximum output: {max_output} tokens")
            
            if model == "deepseek-reasoner":
                print(f"Chain of Thought output limit: {config['cot_output']} tokens")
                print("Supported features: chat, prefix completion")
                print("Note: This model excels at complex reasoning tasks and long context understanding.")
        else:
            print(f"\nInvalid model. Available models: {', '.join(available_models)}")

    def add_function(self, function_json: str) -> None:
        """Add a function definition"""
        try:
            function = json.loads(function_json)
            if len(self.functions) >= 128:
                print("\nError: Maximum number of functions (128) reached")
                return
            self.functions.append(function)
            print(f"\nFunction '{function.get('name', 'unnamed')}' added")
        except json.JSONDecodeError:
            print("\nError: Invalid JSON format for function definition")

    def clear_functions(self) -> None:
        """Clear all registered functions"""
        self.functions = []
        print("\nAll functions cleared")

    def set_temperature(self, temp_str: str) -> None:
        """Set temperature either by number or preset name"""
        try:
            # Try to parse as float first
            temp = float(temp_str)
            if 0 <= temp <= 2:
                self.temperature = temp
                print(f"\nTemperature set to {temp}")
            else:
                print("\nError: Temperature must be between 0 and 2")
        except ValueError:
            # Try as preset name
            preset = temp_str.lower()
            if preset in self.temperature_presets:
                self.temperature = self.temperature_presets[preset]
                print(f"\nTemperature set to {self.temperature} ({preset} preset)")
            else:
                print("\nError: Invalid temperature or preset name")
                print("Available presets:", ", ".join(self.temperature_presets.keys()))

    def display_token_info(self, usage: Dict[str, int]) -> None:
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

    def set_frequency_penalty(self, penalty: float) -> None:
        """Set frequency penalty between -2.0 and 2.0"""
        try:
            penalty = float(penalty)
            if -2.0 <= penalty <= 2.0:
                self.frequency_penalty = penalty
                print(f"\nFrequency penalty set to {penalty}")
            else:
                print("\nError: Frequency penalty must be between -2.0 and 2.0")
        except ValueError:
            print("\nError: Invalid frequency penalty value")

    def set_presence_penalty(self, penalty: float) -> None:
        """Set presence penalty between -2.0 and 2.0"""
        try:
            penalty = float(penalty)
            if -2.0 <= penalty <= 2.0:
                self.presence_penalty = penalty
                print(f"\nPresence penalty set to {penalty}")
            else:
                print("\nError: Presence penalty must be between -2.0 and 2.0")
        except ValueError:
            print("\nError: Invalid presence penalty value")

    def set_top_p(self, top_p: float) -> None:
        """Set top_p between 0.0 and 1.0"""
        try:
            top_p = float(top_p)
            if 0.0 <= top_p <= 1.0:
                self.top_p = top_p
                print(f"\nTop_p set to {top_p}")
            else:
                print("\nError: Top_p must be between 0.0 and 1.0")
        except ValueError:
            print("\nError: Invalid top_p value")

    def add_stop_sequence(self, sequence: str) -> None:
        """Add a stop sequence"""
        if len(self.stop_sequences) >= 16:
            print("\nError: Maximum number of stop sequences (16) reached")
            return
        self.stop_sequences.append(sequence)
        print(f"\nStop sequence added: {sequence}")

    def clear_stop_sequences(self) -> None:
        """Clear all stop sequences"""
        self.stop_sequences = []
        print("\nAll stop sequences cleared")

    def list_models(self) -> None:
        """List available models from the API"""
        try:
            response = self.client.models.list()
            if response.data:
                print("\nAvailable Models:")
                for model in response.data:
                    print(f"  - {model.id} (owned by {model.owned_by})")
            else:
                print("\nNo models available")
        except Exception as e:
            print(f"\nError fetching models: {str(e)}")

    def check_balance(self) -> None:
        """Check and display the user's current balance"""
        try:
            response = self.client.get(
                "https://api-docs.deepseek.com/api/get-user-balance",
                headers={"Authorization": f"Bearer {self.get_api_key()}"}
            )
            if response.status_code == 200:
                balance = response.json()
                print(f"Current balance: {balance}")
            else:
                print(f"Failed to fetch balance. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error checking balance: {str(e)}")

    def display_conversation_state(self) -> None:
        """Display the current conversation state"""
        if not self.messages:
            print("\nNo conversation history.")
            return
            
        print(f"\nConversation Turn: {self.conversation_turn}")
        print("Current conversation history:")
        for msg in self.messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                print(f"\n[System]  {content}")
            elif role == "user":
                print(f"\n[User]    {content}")
            elif role == "assistant":
                print(f"\n[AI]      {content}")
                if "reasoning_content" in msg:
                    print(f"[Reasoning] {msg['reasoning_content']}")

    def handle_command(self, command: str) -> bool:
        """Handle CLI commands"""
        if command in ['quit', 'exit']:
            print("\nGoodbye!")
            return False
        elif command == '/json':
            self.toggle_json_mode()
        elif command == '/stream':
            self.toggle_stream()
        elif command == '/beta':
            self.toggle_beta()
        elif command == '/prefix':
            self.toggle_prefix_mode()
        elif command == '/models':
            self.list_models()
        elif command.startswith('/model '):
            self.switch_model(command.split(' ')[1])
        elif command.startswith('/temp '):
            self.set_temperature(command.split(' ')[1])
        elif command.startswith('/freq '):
            self.set_frequency_penalty(command.split(' ')[1])
        elif command.startswith('/pres '):
            self.set_presence_penalty(command.split(' ')[1])
        elif command.startswith('/top_p '):
            self.set_top_p(command.split(' ')[1])
        elif command.startswith('/stop '):
            self.add_stop_sequence(command[6:])
        elif command == '/clearstop':
            self.clear_stop_sequences()
        elif command.startswith('/function '):
            self.add_function(command[10:])
        elif command == '/clearfuncs':
            self.clear_functions()
        elif command == '/history':
            self.display_conversation_state()
        elif command == '/clear':
            self.messages = [self.messages[0]] if self.messages and self.messages[0]["role"] == "system" else []  # Keep system message if exists
            self.conversation_turn = 0
            print("\nConversation history cleared")
        elif command == '/about':
            print("\nDeepSeek API Information:")
            print("  Documentation:", self.API_DOCS)
            print("  Authentication: Bearer Token")
            print("  Contact:", self.API_CONTACT)
            print("  License:", self.API_LICENSE)
            print("  Terms of Service:", self.API_TERMS)
        elif command == '/fim':
            self.toggle_fim_mode()
        elif command == '/cache':
            self.toggle_context_cache()
        elif command == '/help':
            print("\nAvailable commands:")
            print("  /json        - Toggle JSON output mode")
            print("  /stream      - Toggle streaming mode")
            print("  /beta        - Toggle beta features")
            print("  /prefix      - Toggle prefix completion mode (requires beta)")
            print("  /models      - List available models")
            print("  /model X     - Switch model (deepseek-chat, deepseek-coder, deepseek-reasoner)")
            print("  /temp X      - Set temperature (0-2) or use preset (coding/data/chat/translation/creative)")
            print("  /freq X      - Set frequency penalty (-2 to 2)")
            print("  /pres X      - Set presence penalty (-2 to 2)")
            print("  /top_p X     - Set top_p sampling (0 to 1)")
            print("  /stop X      - Add stop sequence")
            print("  /clearstop   - Clear all stop sequences")
            print("  /function {} - Add a function definition (JSON format)")
            print("  /clearfuncs  - Clear all registered functions")
            print("  /history     - Display current conversation history")
            print("  /clear       - Clear conversation history")
            print("  /about       - Show API information and contact details")
            print("  /fim         - Toggle Fill-in-the-Middle completion mode (requires beta)")
            print("  /cache       - Toggle context caching")
            print("\nNotes:")
            print("  - deepseek-chat is DeepSeek-V3 with 8K token output limit")
            print("  - deepseek-reasoner is DeepSeek-R1 with 64K context and 8K output limit")
            print("  - Temperature presets:")
            print("    coding: 0.0, data: 1.0, chat: 1.3, translation: 1.3, creative: 1.5")
            print("\nFor support, contact:", self.API_CONTACT)
        elif command.startswith("/balance"):
            self.check_balance()
            return True
        else:
            return None
        return True

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

    def handle_api_error(self, e: APIError) -> Optional[str]:
        """Handle different types of API errors with detailed messages"""
        # Get HTTP status code
        status_code = getattr(e, 'status_code', None)
        error_code = getattr(e, 'code', None)
        
        # Define error messages for each status code
        status_messages = {
            400: {
                "message": "Invalid request body format.",
                "solution": "Please modify your request body according to the hints in the error message."
            },
            401: {
                "message": "Authentication fails due to the wrong API key.",
                "solution": "Please check your API key or create a new one if needed."
            },
            402: {
                "message": "Insufficient balance in your account.",
                "solution": "Please check your account balance and top up if needed."
            },
            422: {
                "message": "Invalid parameters in the request.",
                "solution": "Please modify your request parameters according to the error message."
            },
            429: {
                "message": "Rate limit reached - too many requests.",
                "solution": "Please pace your requests. Consider retrying after a brief wait."
            },
            500: {
                "message": "Server error occurred.",
                "solution": "Please retry your request after a brief wait. Contact support if the issue persists."
            },
            503: {
                "message": "Server is currently overloaded.",
                "solution": "Please retry your request after a brief wait."
            }
        }
        
        # Handle rate limit errors with retry
        if isinstance(e, RateLimitError) or status_code == 429:
            retry_after = int(e.headers.get('retry-after', self.retry_delay))
            print(f"\nRate limit exceeded. Retrying in {retry_after} seconds...")
            time.sleep(retry_after)
            return "retry"
        
        # Handle other status codes
        if status_code in status_messages:
            error_info = status_messages[status_code]
            print(f"\nError ({status_code}): {error_info['message']}")
            print(f"Solution: {error_info['solution']}")
            
            # Special handling for specific error codes
            if status_code == 401:
                # Prompt for new API key on authentication failure
                new_key = input("\nWould you like to enter a new API key? (y/n): ")
                if new_key.lower() == 'y':
                    self.client.api_key = input("Please enter your new DeepSeek API key: ")
                    return "retry"
            elif status_code in [500, 503]:
                # Offer automatic retry for server errors
                retry = input("\nWould you like to retry the request? (y/n): ")
                if retry.lower() == 'y':
                    return "retry"
        else:
            # Handle unknown errors
            print(f"\nUnexpected API Error (Code {status_code}): {str(e)}")
            if error_code:
                print(f"Error code: {error_code}")
        
        return None

    def retry_with_exponential_backoff(self, func, *args, **kwargs) -> Optional[str]:
        """Retry function with exponential backoff"""
        current_delay = self.retry_delay
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except APIError as e:
                if attempt == self.max_retries - 1:
                    # On last attempt, just handle the error without retry
                    self.handle_api_error(e)
                    return None
                
                result = self.handle_api_error(e)
                if result == "retry":
                    retry_after = int(getattr(e, 'headers', {}).get('retry-after', current_delay))
                    print(f"\nRetry attempt {attempt + 1}/{self.max_retries} in {retry_after} seconds...")
                    time.sleep(retry_after)
                    current_delay = min(current_delay * 2, self.max_retry_delay)
                    continue
                return None
            except Exception as e:
                print(f"\nUnexpected error: {str(e)}")
                return None
        return None

    def get_completion(self, messages: list) -> Optional[str]:
        """Get completion from the API with retry logic"""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "stream": self.stream,
                "max_tokens": self.max_tokens,
                "context_cache": self.context_cache  # Enable/disable context caching
            }
            
            # Only add parameters if not using reasoning model
            if self.model != "deepseek-reasoner":
                kwargs.update({
                    "temperature": self.temperature,
                    "frequency_penalty": self.frequency_penalty,
                    "presence_penalty": self.presence_penalty,
                    "top_p": self.top_p
                })
                
                if self.json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                    # Add JSON word requirement if needed
                    if self.messages and self.messages[0]["role"] == "system":
                        self.messages[0]["content"] += " Please ensure all responses are valid JSON."
                
                if self.functions:
                    kwargs["tools"] = [{"type": "function", "function": f} for f in self.functions]
            
            if self.stop_sequences:
                kwargs["stop"] = self.stop_sequences
            
            if self.stream:
                kwargs["stream_options"] = self.stream_options

            # Handle prefix mode
            if self.prefix_mode and messages[-1]["role"] == "user":
                prefix_content = messages[-1]["content"]
                messages[-1] = {
                    "role": "assistant",
                    "content": prefix_content,
                    "prefix": True
                }

            # Handle FIM mode
            if self.fim_mode and messages[-1]["role"] == "user":
                content = messages[-1]["content"]
                if "<fim_prefix>" in content and "<fim_suffix>" in content:
                    # Extract prefix and suffix
                    prefix = content.split("<fim_prefix>")[1].split("</fim_prefix>")[0]
                    suffix = content.split("<fim_suffix>")[1].split("</fim_suffix>")[0]
                    messages[-1] = {
                        "role": "assistant",
                        "content": "",
                        "fim_prefix": prefix,
                        "fim_suffix": suffix
                    }

            def make_request():
                response = self.client.chat.completions.create(**kwargs)
                if self.stream:
                    return self.stream_response(response)
                else:
                    if not self.stream:
                        self.display_token_info(response.usage.model_dump())
                    
                    # Handle reasoning model response
                    if self.model == "deepseek-reasoner" and hasattr(response.choices[0].message, "reasoning_content"):
                        content = response.choices[0].message.content
                        reasoning = response.choices[0].message.reasoning_content
                        # Store reasoning content in message history
                        self.messages.append({
                            "role": "assistant",
                            "content": content,
                            "reasoning_content": reasoning
                        })
                        # Display reasoning if not in stream mode
                        if not self.stream:
                            print("\nReasoning:", reasoning)
                        return content
                    elif response.choices[0].function_call:
                        return json.dumps(response.choices[0].function_call, indent=2)
                    return response.choices[0].message.content

            response = self.retry_with_exponential_backoff(make_request)
            if response:
                self.conversation_turn += 1
            return response

        except RateLimitExceeded as e:
            print(f"\nError: {str(e)}")
            return None
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            return None

    def run(self):
        """Run the CLI interface"""
        self.set_system_message("You are a helpful assistant.")
        
        print("Welcome to DeepSeek CLI! (Type '/help' for commands)")
        print("-" * 50)
        
        while True:
            user_input = input("\nYou: ").strip()
            
            # Handle commands
            command_result = self.handle_command(user_input)
            if command_result is False:  # Exit
                break
            elif command_result is True:  # Command handled
                continue
            
            # Add user message to history
            self.messages.append({"role": "user", "content": user_input})
            
            # Get and handle response
            assistant_response = self.get_completion(self.messages)
            if assistant_response:
                if self.json_mode and not self.stream:
                    try:
                        # Pretty print JSON response
                        parsed = json.loads(assistant_response)
                        print("\nAssistant:", json.dumps(parsed, indent=2))
                    except json.JSONDecodeError:
                        print("\nAssistant:", assistant_response)
                elif not self.stream:
                    print("\nAssistant:", assistant_response)
                
                # Add assistant response to history
                self.messages.append({"role": "assistant", "content": assistant_response})

def main():
    cli = DeepSeekCLI()
    cli.run()

if __name__ == "__main__":
    main() 