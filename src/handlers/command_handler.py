"""Command handler for DeepSeek CLI"""

import json
from typing import Optional, Dict, Any, Tuple

# Add proper import paths for both development and installed modes
try:
    # When running as an installed package
    from api.client import APIClient
    from handlers.chat_handler import ChatHandler
    from config.settings import API_CONTACT, API_LICENSE, API_TERMS, API_DOCS
except ImportError:
    # When running in development mode
    from src.api.client import APIClient
    from src.handlers.chat_handler import ChatHandler
    from src.config.settings import API_CONTACT, API_LICENSE, API_TERMS, API_DOCS

class CommandHandler:
    def __init__(self, api_client: APIClient, chat_handler: ChatHandler):
        self.api_client = api_client
        self.chat_handler = chat_handler

    def handle_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """Handle CLI commands and return (should_continue, message)"""
        command = command.strip().lower()  # Normalize input
        if not command:
            return True, None

        if command in ['quit', 'exit']:
            return False, "Goodbye!"

        elif command == '/json':
            self.chat_handler.toggle_json_mode()
            return True, f"JSON mode {'enabled' if self.chat_handler.json_mode else 'disabled'}"

        elif command == '/stream':
            self.chat_handler.toggle_stream()
            return True, f"Streaming {'enabled' if self.chat_handler.stream else 'disabled'}"

        elif command == '/beta':
            self.api_client.toggle_beta()
            return True, f"Beta mode {'enabled' if self.api_client.beta_mode else 'disabled'}"

        elif command == '/prefix':
            if not self.api_client.beta_mode:
                return True, "Error: Prefix mode requires beta mode. Use /beta first."
            self.chat_handler.prefix_mode = not self.chat_handler.prefix_mode
            return True, f"Prefix mode {'enabled' if self.chat_handler.prefix_mode else 'disabled'}"

        elif command == '/models':
            try:
                response = self.api_client.list_models()
                if response.data:
                    models = "\n".join(f"  - {model.id} (owned by {model.owned_by})" for model in response.data)
                    return True, f"Available Models:\n{models}"
                return True, "No models available"
            except Exception as e:
                return True, f"Error fetching models: {str(e)}"

        elif command.startswith('/model '):
            model = command.split(' ')[1]
            if self.chat_handler.switch_model(model):
                return True, f"Switched to {model} model\nMax tokens set to {self.chat_handler.max_tokens}"
            return True, "Invalid model"

        elif command.startswith('/temp '):
            temp_str = command.split(' ')[1]
            if self.chat_handler.set_temperature(temp_str):
                return True, f"Temperature set to {self.chat_handler.temperature}"
            return True, "Invalid temperature value or preset"

        elif command.startswith('/freq '):
            try:
                penalty = float(command.split(' ')[1])
                if self.chat_handler.set_frequency_penalty(penalty):
                    return True, f"Frequency penalty set to {penalty}"
                return True, "Frequency penalty must be between -2.0 and 2.0"
            except ValueError:
                return True, "Invalid frequency penalty value"

        elif command.startswith('/pres '):
            try:
                penalty = float(command.split(' ')[1])
                if self.chat_handler.set_presence_penalty(penalty):
                    return True, f"Presence penalty set to {penalty}"
                return True, "Presence penalty must be between -2.0 and 2.0"
            except ValueError:
                return True, "Invalid presence penalty value"

        elif command.startswith('/top_p '):
            try:
                top_p = float(command.split(' ')[1])
                if self.chat_handler.set_top_p(top_p):
                    return True, f"Top_p set to {top_p}"
                return True, "Top_p must be between 0.0 and 1.0"
            except ValueError:
                return True, "Invalid top_p value"

        elif command.startswith('/stop '):
            sequence = command[6:]
            if self.chat_handler.add_stop_sequence(sequence):
                return True, f"Stop sequence added: {sequence}"
            return True, "Maximum number of stop sequences reached"

        elif command == '/clearstop':
            self.chat_handler.clear_stop_sequences()
            return True, "All stop sequences cleared"

        elif command.startswith('/function '):
            try:
                function = json.loads(command[10:])
                if self.chat_handler.add_function(function):
                    return True, f"Function '{function.get('name', 'unnamed')}' added"
                return True, "Maximum number of functions reached"
            except json.JSONDecodeError:
                return True, "Invalid JSON format for function definition"

        elif command == '/clearfuncs':
            self.chat_handler.clear_functions()
            return True, "All functions cleared"

        elif command == '/clear':
            self.chat_handler.clear_history()
            return True, "Conversation history cleared"

        elif command == '/help':
            return True, self.get_help_message()

        elif command == '/about':
            return True, self.get_about_message()

        return None, None

    def get_help_message(self) -> str:
        """Get help message"""
        return """Available commands:
  /json        - Toggle JSON output mode
  /stream      - Toggle streaming mode
  /beta        - Toggle beta features
  /prefix      - Toggle prefix completion mode (requires beta)
  /models      - List available models
  /model X     - Switch model (deepseek-chat, deepseek-coder, deepseek-reasoner)
  /temp X      - Set temperature (0-2) or use preset (coding/data/chat/translation/creative)
  /freq X      - Set frequency penalty (-2 to 2)
  /pres X      - Set presence penalty (-2 to 2)
  /top_p X     - Set top_p sampling (0 to 1)
  /stop X      - Add stop sequence
  /clearstop   - Clear all stop sequences
  /function {} - Add a function definition (JSON format)
  /clearfuncs  - Clear all registered functions
  /clear       - Clear conversation history
  /about       - Show API information and contact details
  /help        - Show this help message
  quit         - Exit the program

Notes:
  - deepseek-chat is DeepSeek-V3 with 8K token output limit
  - deepseek-reasoner is DeepSeek-R1 with 64K context and 8K output limit
  - Temperature presets:
    coding: 0.0, data: 1.0, chat: 1.3, translation: 1.3, creative: 1.5"""

    def get_about_message(self) -> str:
        """Get about message"""
        return f"""DeepSeek API Information:
  Documentation: {API_DOCS}
  Authentication: Bearer Token
  Contact: {API_CONTACT}
  License: {API_LICENSE}
  Terms of Service: {API_TERMS}"""