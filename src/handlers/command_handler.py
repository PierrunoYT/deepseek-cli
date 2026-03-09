"""Command handler for DeepSeek CLI"""

import json
from typing import Optional, Dict, Any, Tuple

# Simplified import handling with clear fallback chain
try:
    # When installed via pip/pipx (package_dir={"": "src"})
    from api.client import APIClient
    from handlers.chat_handler import ChatHandler
    from config.settings import API_CONTACT, API_LICENSE, API_TERMS, API_DOCS
except ImportError:
    # When running from source (development mode)
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
            return True, f"Beta mode {'enabled' if self.api_client.beta_mode else 'disabled'} (Note: Most features are now stable and don't require beta mode)"

        elif command_lower == '/prefix':
            self.chat_handler.prefix_mode = not self.chat_handler.prefix_mode
            return True, f"Prefix mode {'enabled' if self.chat_handler.prefix_mode else 'disabled'}"

        elif command_lower == '/models':
            try:
                response = self.api_client.list_models()
                if response.data:
                    models = "\n".join(f"  - {model.id} (owned by {model.owned_by})" for model in response.data)
                    return True, f"Available Models:\n{models}"
                return True, "No models available"
            except Exception as e:
                return True, f"Error fetching models: {str(e)}"

        elif command_lower.startswith('/model '):
            parts = command_raw.split(' ', 1)
            model = parts[1].strip() if len(parts) > 1 else ''
            if self.chat_handler.switch_model(model):
                return True, f"Switched to {model} model\nMax tokens set to {self.chat_handler.max_tokens}"
            return True, "Invalid model"

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

        elif command_lower.startswith('/system '):
            message = command_raw[8:].strip()
            if message:
                self.chat_handler.set_system_message(message)
                return True, f"System message set to: {message}"
            return True, "Usage: /system <message>"

        elif command_lower == '/system':
            current = (self.chat_handler.messages[0]["content"]
                       if self.chat_handler.messages and self.chat_handler.messages[0]["role"] == "system"
                       else "(none)")
            return True, f"Current system message: {current}"

        elif command_lower == '/clear':
            self.chat_handler.clear_history()
            return True, "Conversation history cleared"

        elif command_lower == '/history':
            if not self.chat_handler.messages:
                return True, "No conversation history"
            lines = []
            for i, msg in enumerate(self.chat_handler.messages):
                role = msg.get("role", "unknown").capitalize()
                content = msg.get("content", "")
                # Truncate very long messages for readability
                preview = content[:200] + ("..." if len(content) > 200 else "")
                lines.append(f"  [{i}] {role}: {preview}")
            return True, "Conversation history:\n" + "\n".join(lines)

        elif command_lower == '/fim':
            self.chat_handler.fim_mode = not getattr(self.chat_handler, 'fim_mode', False)
            return True, f"FIM (Fill-in-the-Middle) mode {'enabled' if self.chat_handler.fim_mode else 'disabled'}"

        elif command_lower == '/cache':
            return True, "Context caching is handled automatically by the DeepSeek API and requires no manual toggling."

        elif command_lower == '/balance':
            return True, (
                "Account balance check is not available via this CLI.\n"
                "Please visit https://platform.deepseek.com to view your balance."
            )

        elif command_lower == '/help':
            return True, self.get_help_message()

        elif command_lower == '/about':
            return True, self.get_about_message()

        return None, None

    def get_help_message(self) -> str:
        """Get help message with all available commands"""
        return """Available commands:
  /json        - Toggle JSON output mode
  /stream      - Toggle streaming mode
  /beta        - Toggle beta API endpoint
  /prefix      - Toggle prefix completion mode (last user msg becomes assistant prefix)
  /fim         - Toggle Fill-in-the-Middle mode (use <fim_prefix>/<fim_suffix> tags)
  /cache       - Show context caching status (automatic, no toggle needed)
  /models      - List available models
  /model X     - Switch model (deepseek-chat, deepseek-coder, deepseek-reasoner)
  /temp X      - Set temperature (0-2) or preset (coding/data/chat/translation/creative)
  /freq X      - Set frequency penalty (-2 to 2)
  /pres X      - Set presence penalty (-2 to 2)
  /top_p X     - Set top_p sampling (0 to 1)
  /stop X      - Add stop sequence
  /clearstop   - Clear all stop sequences
  /function {} - Add a function definition (JSON format)
  /clearfuncs  - Clear all registered functions
  /system      - Show the current system message
  /system X    - Set a custom system message
  /clear       - Clear conversation history
  /history     - Display conversation history
  /balance     - Show account balance instructions
  /about       - Show API information and contact details
  /help        - Show this help message
  quit/exit    - Exit the program

Notes:
  - deepseek-chat is DeepSeek-V3.2 (Non-thinking Mode) with 128K context, 8K output
  - deepseek-reasoner is DeepSeek-V3.2 (Thinking Mode) with 128K context, 64K output
  - deepseek-coder is DeepSeek-V2.5 (may redirect to deepseek-chat)
  - Temperature presets:
    coding: 0.0, data: 1.0, chat: 1.3, translation: 1.3, creative: 1.5
  - Context caching is automatic on the DeepSeek API (no manual toggle required)"""

    def get_about_message(self) -> str:
        """Get about message with API information"""
        return f"""DeepSeek API Information:
  Documentation: {API_DOCS}
  Authentication: Bearer Token
  Contact: {API_CONTACT}
  License: {API_LICENSE}
  Terms of Service: {API_TERMS}"""