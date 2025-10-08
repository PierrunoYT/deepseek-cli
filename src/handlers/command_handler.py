"""Command handler for DeepSeek CLI"""

import json
from typing import Optional, Dict, Any, Tuple

# Simplified import handling with clear fallback chain
try:
    from deepseek_cli.api.client import APIClient
    from deepseek_cli.handlers.chat_handler import ChatHandler
    from deepseek_cli.config.settings import API_CONTACT, API_LICENSE, API_TERMS, API_DOCS
except ImportError:
    from src.api.client import APIClient
    from src.handlers.chat_handler import ChatHandler
    from src.config.settings import API_CONTACT, API_LICENSE, API_TERMS, API_DOCS

class CommandHandler:
    def __init__(self, api_client: APIClient, chat_handler: ChatHandler) -> None:
        self.api_client = api_client
        self.chat_handler = chat_handler

    def handle_command(self, command: str) -> Tuple[Optional[bool], Optional[str]]:
        """Handle CLI commands and return (should_continue, message)
        
        Args:
            command: The command string to process
            
        Returns:
            Tuple[Optional[bool], Optional[str]]: (should_continue, message)
                - (False, message): Exit the program
                - (True, message): Command handled, continue
                - (None, None): Not a command, process as user input
        """
        command_raw = command.strip()
        if not command_raw:
            return True, None

        command_lower = command_raw.lower()

        if command_lower in ['quit', 'exit']:
            return False, "Goodbye!"

        elif command_lower == '/json':
            self.chat_handler.toggle_json_mode()
            return True, f"JSON mode {'enabled' if self.chat_handler.json_mode else 'disabled'}"

        elif command_lower == '/stream':
            self.chat_handler.toggle_stream()
            return True, f"Streaming {'enabled' if self.chat_handler.stream else 'disabled'}"

        elif command_lower == '/beta':
            self.api_client.toggle_beta()
            return True, f"Beta mode {'enabled' if self.api_client.beta_mode else 'disabled'}"

        elif command_lower == '/prefix':
            if not self.api_client.beta_mode:
                return True, "Error: Prefix mode requires beta mode. Use /beta first."
            self.chat_handler.prefix_mode = not self.chat_handler.prefix_mode
            return True, f"Prefix mode {'enabled' if self.chat_handler.prefix_mode else 'disabled'}"

        elif command_lower == '/models':
            try:
                models = self.api_client.list_available_models()
                if models:
                    # Group models by provider
                    providers = {}
                    for model in models:
                        provider = model["provider"]
                        if provider not in providers:
                            providers[provider] = []
                        providers[provider].append(model)
                    
                    output = "Available Models:\n"
                    for provider, provider_models in sorted(providers.items()):
                        output += f"\n[{provider.upper()}]\n"
                        for model in provider_models:
                            output += f"  - {model['name']}\n"
                            output += f"    {model['description']}\n"
                    return True, output
                return True, "No models available"
            except Exception as e:
                return True, f"Error fetching models: {str(e)}"
        
        elif command_lower.startswith('/provider '):
            parts = command_raw.split(' ', 1)
            provider = parts[1].strip() if len(parts) > 1 else ''
            try:
                models = self.api_client.list_models_by_provider(provider)
                if models:
                    output = f"Models for {provider.upper()}:\n"
                    for model in models:
                        output += f"  - {model['name']}\n"
                        output += f"    {model['description']}\n"
                    return True, output
                return True, f"No models found for provider: {provider}"
            except Exception as e:
                return True, f"Error: {str(e)}"

        elif command_lower.startswith('/model '):
            parts = command_raw.split(' ', 1)
            model = parts[1].strip() if len(parts) > 1 else ''
            if self.chat_handler.switch_model(model):
                self.api_client.set_model(model)
                model_info = self.api_client.get_model_info(model)
                provider = model_info.get("provider", "unknown") if model_info else "unknown"
                display_name = model_info.get("display_name", model) if model_info else model
                return True, f"Switched to {display_name} ({provider})\nMax tokens set to {self.chat_handler.max_tokens}"
            return True, "Invalid model. Use /models to see available models."
        
        elif command_lower.startswith('/apikey '):
            parts = command_raw.split(' ', 2)
            if len(parts) < 3:
                return True, "Usage: /apikey <provider> <key>"
            provider = parts[1].strip().lower()
            api_key = parts[2].strip()
            try:
                self.api_client.update_api_key(provider, api_key)
                return True, f"API key updated for {provider}"
            except Exception as e:
                return True, f"Error updating API key: {str(e)}"

        elif command_lower.startswith('/temp '):
            parts = command_raw.split(' ', 1)
            temp_str = parts[1].strip() if len(parts) > 1 else ''
            if self.chat_handler.set_temperature(temp_str):
                return True, f"Temperature set to {self.chat_handler.temperature}"
            return True, "Invalid temperature value or preset"

        elif command_lower.startswith('/freq '):
            try:
                penalty = float(command_raw.split(' ', 1)[1])
                if self.chat_handler.set_frequency_penalty(penalty):
                    return True, f"Frequency penalty set to {penalty}"
                return True, "Frequency penalty must be between -2.0 and 2.0"
            except (ValueError, IndexError):
                return True, "Invalid frequency penalty value"

        elif command_lower.startswith('/pres '):
            try:
                penalty = float(command_raw.split(' ', 1)[1])
                if self.chat_handler.set_presence_penalty(penalty):
                    return True, f"Presence penalty set to {penalty}"
                return True, "Presence penalty must be between -2.0 and 2.0"
            except (ValueError, IndexError):
                return True, "Invalid presence penalty value"

        elif command_lower.startswith('/top_p '):
            try:
                top_p = float(command_raw.split(' ', 1)[1])
                if self.chat_handler.set_top_p(top_p):
                    return True, f"Top_p set to {top_p}"
                return True, "Top_p must be between 0.0 and 1.0"
            except (ValueError, IndexError):
                return True, "Invalid top_p value"

        elif command_lower.startswith('/stop '):
            sequence = command_raw[6:]
            if self.chat_handler.add_stop_sequence(sequence):
                return True, f"Stop sequence added: {sequence}"
            return True, "Maximum number of stop sequences reached"

        elif command_lower == '/clearstop':
            self.chat_handler.clear_stop_sequences()
            return True, "All stop sequences cleared"

        elif command_lower.startswith('/function '):
            try:
                function = json.loads(command_raw[10:])
                if self.chat_handler.add_function(function):
                    return True, f"Function '{function.get('name', 'unnamed')}' added"
                return True, "Maximum number of functions reached"
            except json.JSONDecodeError:
                return True, "Invalid JSON format for function definition"

        elif command_lower == '/clearfuncs':
            self.chat_handler.clear_functions()
            return True, "All functions cleared"

        elif command_lower == '/clear':
            self.chat_handler.clear_history()
            return True, "Conversation history cleared"

        elif command_lower == '/help':
            return True, self.get_help_message()

        elif command_lower == '/about':
            return True, self.get_about_message()

        return None, None

    def get_help_message(self) -> str:
        """Get help message with all available commands"""
        return """Available commands:

Model Management:
  /models      - List all available models grouped by provider
  /provider X  - List models for a specific provider (deepseek, openai, anthropic, gemini, ollama)
  /model X     - Switch to a specific model (use full model name from /models)
  /apikey X Y  - Set API key for provider X with key Y

Output Control:
  /json        - Toggle JSON output mode
  /stream      - Toggle streaming mode
  /beta        - Toggle beta features (DeepSeek only)
  /prefix      - Toggle prefix completion mode (requires beta)

Model Parameters:
  /temp X      - Set temperature (0-2) or use preset (coding/data/chat/translation/creative)
  /freq X      - Set frequency penalty (-2 to 2)
  /pres X      - Set presence penalty (-2 to 2)
  /top_p X     - Set top_p sampling (0 to 1)
  /stop X      - Add stop sequence
  /clearstop   - Clear all stop sequences

Function Calling:
  /function {} - Add a function definition (JSON format)
  /clearfuncs  - Clear all registered functions

General:
  /clear       - Clear conversation history
  /about       - Show API information and contact details
  /help        - Show this help message
  quit/exit    - Exit the program

Supported Providers:
  - DeepSeek: deepseek/deepseek-chat, deepseek/deepseek-coder, deepseek/deepseek-reasoner
  - OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo
  - Anthropic: claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022
  - Google: gemini/gemini-2.0-flash-exp, gemini/gemini-1.5-pro
  - Ollama: ollama/llama3.2, ollama/qwen2.5 (local models)

Temperature Presets:
  coding: 0.0, data: 1.0, chat: 1.3, translation: 1.3, creative: 1.5"""

    def get_about_message(self) -> str:
        """Get about message with API information"""
        return f"""DeepSeek API Information:
  Documentation: {API_DOCS}
  Authentication: Bearer Token
  Contact: {API_CONTACT}
  License: {API_LICENSE}
  Terms of Service: {API_TERMS}"""