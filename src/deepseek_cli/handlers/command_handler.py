"""Command handler for DeepSeek CLI"""

import json
import os
import shlex
from typing import Optional, Dict, Any, Tuple

from deepseek_cli.api.client import APIClient
from deepseek_cli.handlers.chat_handler import ChatHandler
from deepseek_cli.handlers.file_handler import FileHandler, pick_files
from deepseek_cli.config.settings import (
    API_CONTACT,
    API_LICENSE,
    API_TERMS,
    API_DOCS,
    MODEL_CONFIGS,
    REASONING_EFFORT_LEVELS,
)

class CommandHandler:
    def __init__(
        self,
        api_client: APIClient,
        chat_handler: ChatHandler,
        file_handler: Optional[FileHandler] = None,
    ) -> None:
        self.api_client = api_client
        self.chat_handler = chat_handler
        self.file_handler = file_handler if file_handler is not None else FileHandler()

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

        if command_lower in ['quit', 'exit', '/quit', '/exit']:
            return False, "Goodbye!"

        elif command_lower == '/multiline':
            # This would need access to the CLI instance, so for now we'll provide guidance
            return True, "Multiline mode can be enabled via --multiline flag when starting the CLI"

        elif command_lower == '/raw':
            self.chat_handler.raw_mode = not self.chat_handler.raw_mode
            return True, f"Raw mode {'enabled' if self.chat_handler.raw_mode else 'disabled'}"

        elif command_lower == '/json':
            self.chat_handler.toggle_json_mode()
            return True, f"JSON mode {'enabled' if self.chat_handler.json_mode else 'disabled'}"

        elif command_lower == '/stream':
            self.chat_handler.toggle_stream()
            return True, f"Streaming {'enabled' if self.chat_handler.stream else 'disabled'}"

        elif command_lower == '/beta':
            self.api_client.toggle_beta()
            return True, (
                f"Beta mode {'enabled' if self.api_client.beta_mode else 'disabled'} "
                f"(required for /prefix and /fim; the CLI enables it automatically "
                f"when those are in use)"
            )

        elif command_lower == '/prefix':
            self.chat_handler.prefix_mode = not self.chat_handler.prefix_mode
            self.chat_handler.save_state()
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

        elif command_lower.startswith('/freq') or command_lower.startswith('/pres'):
            # Retained so the commands give an explanation rather than an
            # "unknown command" fall-through into a chat message.
            return True, (
                "The DeepSeek API no longer supports frequency_penalty or "
                "presence_penalty; these parameters are ignored server-side, so "
                "this CLI no longer sends them. Use /temp or /top_p instead."
            )

        elif command_lower == '/think':
            self.chat_handler.toggle_thinking()
            state = 'enabled' if self.chat_handler.thinking else 'disabled'
            return True, (
                f"Thinking mode {state} "
                f"(reasoning effort: {self.chat_handler.reasoning_effort})"
            )

        elif command_lower.startswith('/effort '):
            effort = command_raw[8:].strip()
            if self.chat_handler.set_reasoning_effort(effort):
                return True, f"Reasoning effort set to {self.chat_handler.reasoning_effort}"
            return True, (
                "Invalid effort. Choose one of: "
                + ", ".join(REASONING_EFFORT_LEVELS)
            )

        elif command_lower.startswith('/maxtokens '):
            try:
                value = int(command_raw.split(' ', 1)[1].strip())
            except (ValueError, IndexError):
                return True, "Invalid max tokens value"
            if self.chat_handler.set_max_tokens(value):
                return True, f"Max output tokens set to {self.chat_handler.max_tokens}"
            limit = MODEL_CONFIGS[self.chat_handler.model]["max_tokens"]
            return True, f"Max tokens must be between 1 and {limit}"

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
                self.chat_handler.save_state()
                return True, f"Stop sequence added: {sequence}"
            return True, "Maximum number of stop sequences reached"

        elif command_lower == '/clearstop':
            self.chat_handler.clear_stop_sequences()
            self.chat_handler.save_state()
            return True, "All stop sequences cleared"

        elif command_lower.startswith('/function '):
            try:
                function = json.loads(command_raw[10:])
                if self.chat_handler.add_function(function):
                    self.chat_handler.save_state()
                    return True, f"Function '{function.get('name', 'unnamed')}' added"
                return True, "Maximum number of functions reached"
            except json.JSONDecodeError:
                return True, "Invalid JSON format for function definition"

        elif command_lower == '/clearfuncs':
            self.chat_handler.clear_functions()
            self.chat_handler.save_state()
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
            self.chat_handler.save_state()
            return True, "Conversation history cleared"

        elif command_lower == '/history':
            if not self.chat_handler.messages:
                return True, "No conversation history"
            lines = []
            for i, msg in enumerate(self.chat_handler.messages):
                role = str(msg.get("role", "unknown")).capitalize()
                # content may be absent or non-string on a hand-edited or
                # corrupted history file; str() keeps /history from raising.
                content = msg.get("content") or ""
                if not isinstance(content, str):
                    content = str(content)
                # Truncate very long messages for readability
                preview = content[:200] + ("..." if len(content) > 200 else "")
                lines.append(f"  [{i}] {role}: {preview}")
            return True, "Conversation history:\n" + "\n".join(lines)

        elif command_lower == '/fim':
            self.chat_handler.fim_mode = not self.chat_handler.fim_mode
            self.chat_handler.save_state()
            return True, f"FIM (Fill-in-the-Middle) mode {'enabled' if self.chat_handler.fim_mode else 'disabled'}"

        elif command_lower == '/cache':
            return True, "Context caching is handled automatically by the DeepSeek API and requires no manual toggling."

        elif command_lower == '/balance':
            return True, (
                "Account balance check is not available via this CLI.\n"
                "Please visit https://platform.deepseek.com to view your balance."
            )

        elif command_lower == '/files':
            files = self.file_handler.list_attachments()
            if not files:
                return True, "No files attached. Use /file <path>, /file <glob>, or /pick to attach."
            lines = ["Attached files (will be sent with next message):"]
            for i, f in enumerate(files):
                size = int(f.get("size", 0))
                lines.append(f"  [{i}] {f['path']}  ({size} bytes)")
            total = self.file_handler.total_size()
            lines.append(f"Total: {len(files)} file(s), {total} bytes")
            return True, "\n".join(lines)

        elif command_lower == '/file' or command_lower.startswith('/file '):
            arg = command_raw[5:].strip() if len(command_raw) > 5 else ""
            if not arg:
                return True, (
                    "Usage: /file <path-or-glob> [more paths...]\n"
                    "  Examples:\n"
                    "    /file src/main.py\n"
                    "    /file src/*.py\n"
                    "    /file ~/notes/todo.md README.md\n"
                    "  Tip: use /pick for an interactive picker with tab completion."
                )
            try:
                tokens = shlex.split(arg, posix=(os.name != "nt"))
            except ValueError:
                tokens = arg.split()
            return True, self._attach_and_summarize(tokens)

        elif command_lower == '/pick':
            tokens = pick_files()
            if not tokens:
                return True, "Picker cancelled. No files attached."
            return True, self._attach_and_summarize(tokens)

        elif command_lower == '/dropfile' or command_lower.startswith('/dropfile '):
            arg = command_raw[9:].strip() if len(command_raw) > 9 else ""
            if not arg:
                return True, "Usage: /dropfile <index-or-path>  (see /files for indices)"
            if self.file_handler.remove(arg):
                return True, f"Removed attachment: {arg}"
            return True, f"No attachment matching: {arg}"

        elif command_lower == '/clearfiles':
            count = len(self.file_handler.list_attachments())
            self.file_handler.clear()
            return True, f"Cleared {count} attached file(s)"

        elif command_lower == '/help':
            return True, self.get_help_message()

        elif command_lower == '/about':
            return True, self.get_about_message()

        return None, None

    def _attach_and_summarize(self, patterns: list) -> str:
        """Run FileHandler.attach() over each pattern and build a status report."""
        # A leading --allow-sensitive opts in to attaching credential-shaped
        # files, which are refused by default.
        allow_sensitive = False
        patterns = list(patterns)
        if "--allow-sensitive" in patterns:
            allow_sensitive = True
            patterns = [p for p in patterns if p != "--allow-sensitive"]

        if not patterns:
            return "No paths supplied."
        attached_all: list = []
        errors_all: list = []
        for pattern in patterns:
            attached, errors = self.file_handler.attach(
                pattern, allow_sensitive=allow_sensitive
            )
            attached_all.extend(attached)
            errors_all.extend(errors)

        lines = []
        if attached_all:
            lines.append(f"Attached {len(attached_all)} file(s):")
            for p in attached_all:
                lines.append(f"  + {p}")
        if errors_all:
            if lines:
                lines.append("")
            lines.append("Issues:")
            for e in errors_all:
                lines.append(f"  ! {e}")
        if not lines:
            lines.append("No files attached.")
        total = self.file_handler.total_size()
        count = len(self.file_handler.list_attachments())
        lines.append("")
        lines.append(f"Currently attached: {count} file(s), {total} bytes "
                     f"(use /files to list, /clearfiles to clear).")
        return "\n".join(lines)

    def get_help_message(self) -> str:
        """Get help message with all available commands"""
        return """Available commands:
  /multiline    - Show multiline mode information (enable with --multiline flag)
  /raw         - Toggle raw output mode (bypass formatting for edge cases)
  /json        - Toggle JSON output mode
  /stream      - Toggle streaming mode
  /beta        - Toggle beta API endpoint (required for /prefix and /fim)
  /prefix      - Toggle prefix completion mode (last user msg becomes assistant prefix)
  /fim         - Toggle Fill-in-the-Middle mode (use <fim_prefix>/<fim_suffix> tags)
  /think       - Toggle Thinking mode (replaces the retired deepseek-reasoner)
  /effort X    - Set reasoning effort: low, high, max (used when /think is on)
  /cache       - Show context caching status (automatic, no toggle needed)
  /models      - List available models
  /model X     - Switch model (deepseek-v4-flash, deepseek-v4-pro,
                 deepseek-v4-flash-vision-exp)
  /maxtokens N - Set max output tokens for this session
  /temp X      - Set temperature (0-2) or preset (coding/data/chat/translation/creative)
  /top_p X     - Set top_p sampling (0 to 1)
  /stop X      - Add stop sequence
  /clearstop   - Clear all stop sequences
  /function {} - Add a function definition (JSON format)
  /clearfuncs  - Clear all registered functions
  /system      - Show the current system message
  /system X    - Set a custom system message
  /clear       - Clear conversation history
  /history     - Display conversation history
  /file P...   - Attach file(s) for the next message (paths/globs, e.g. src/*.py)
                 Secret-looking files (.env, ~/.ssh/id_rsa, *.pem) are refused;
                 pass --allow-sensitive to override.
  /pick        - Open an interactive file picker (tab completion, multi-select)
  /files       - List currently attached files
  /dropfile X  - Remove an attached file by index (see /files) or path
  /clearfiles  - Clear all attached files
  /balance     - Show account balance instructions
  /about       - Show API information and contact details
  /help        - Show this help message
  /quit, /exit - Exit the program
  quit, exit   - Exit the program

Notes:
  - deepseek-v4-flash: 284B total / 13B active, 1M context, 384K max output
  - deepseek-v4-pro: 1.6T total / 49B active, 1M context, 384K max output
  - deepseek-v4-flash-vision-exp: experimental image-input variant (this CLI
    sends text only)
  - Thinking is a per-request mode on all V4 models, set with /think and
    /effort. The old deepseek-chat / deepseek-reasoner / deepseek-coder names
    were retired on 2026-07-24 and now map to deepseek-v4-flash.
  - frequency_penalty / presence_penalty are no longer supported by the API,
    so /freq and /pres have been removed.
  - /prefix and /fim are Beta-only; the CLI switches to the beta endpoint
    automatically when you use them. FIM output is capped at 4K tokens.
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