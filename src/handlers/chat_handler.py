"""Chat handler for DeepSeek CLI"""

from typing import Optional, Dict, Any, List
from ..config.settings import (
    MODEL_CONFIGS,
    TEMPERATURE_PRESETS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    MAX_FUNCTIONS,
    MAX_STOP_SEQUENCES
)

class ChatHandler:
    def __init__(self):
        self.messages = []
        self.model = "deepseek-chat"
        self.stream = False
        self.json_mode = False
        self.max_tokens = DEFAULT_MAX_TOKENS
        self.functions = []
        self.prefix_mode = False
        self.temperature = DEFAULT_TEMPERATURE
        self.frequency_penalty = 0.0
        self.presence_penalty = 0.0
        self.top_p = 1.0
        self.stop_sequences = []
        self.stream_options = {"include_usage": True}

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

    def toggle_stream(self) -> None:
        """Toggle streaming mode"""
        self.stream = not self.stream

    def switch_model(self, model: str) -> bool:
        """Switch between available models"""
        if model in MODEL_CONFIGS:
            self.model = model
            self.max_tokens = MODEL_CONFIGS[model]["max_tokens"]
            return True
        return False

    def set_temperature(self, temp_str: str) -> bool:
        """Set temperature either by number or preset name"""
        try:
            # Try to parse as float first
            temp = float(temp_str)
            if 0 <= temp <= 2:
                self.temperature = temp
                return True
            return False
        except ValueError:
            # Try as preset name
            preset = temp_str.lower()
            if preset in TEMPERATURE_PRESETS:
                self.temperature = TEMPERATURE_PRESETS[preset]
                return True
            return False

    def set_frequency_penalty(self, penalty: float) -> bool:
        """Set frequency penalty between -2.0 and 2.0"""
        if -2.0 <= penalty <= 2.0:
            self.frequency_penalty = penalty
            return True
        return False

    def set_presence_penalty(self, penalty: float) -> bool:
        """Set presence penalty between -2.0 and 2.0"""
        if -2.0 <= penalty <= 2.0:
            self.presence_penalty = penalty
            return True
        return False

    def set_top_p(self, top_p: float) -> bool:
        """Set top_p between 0.0 and 1.0"""
        if 0.0 <= top_p <= 1.0:
            self.top_p = top_p
            return True
        return False

    def add_function(self, function: Dict[str, Any]) -> bool:
        """Add a function definition"""
        if len(self.functions) >= MAX_FUNCTIONS:
            return False
        self.functions.append(function)
        return True

    def clear_functions(self) -> None:
        """Clear all registered functions"""
        self.functions = []

    def add_stop_sequence(self, sequence: str) -> bool:
        """Add a stop sequence"""
        if len(self.stop_sequences) >= MAX_STOP_SEQUENCES:
            return False
        self.stop_sequences.append(sequence)
        return True

    def clear_stop_sequences(self) -> None:
        """Clear all stop sequences"""
        self.stop_sequences = []

    def clear_history(self) -> None:
        """Clear conversation history but keep system message"""
        if self.messages and self.messages[0]["role"] == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []

    def prepare_chat_request(self) -> Dict[str, Any]:
        """Prepare chat completion request parameters"""
        kwargs = {
            "model": self.model,
            "messages": self.messages,
            "stream": self.stream,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "top_p": self.top_p
        }
        
        if self.json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        if self.functions:
            kwargs["tools"] = [{"type": "function", "function": f} for f in self.functions]
        
        if self.stop_sequences:
            kwargs["stop"] = self.stop_sequences
        
        if self.stream:
            kwargs["stream_options"] = self.stream_options

        # Handle prefix mode
        if self.prefix_mode and self.messages and self.messages[-1]["role"] == "user":
            prefix_content = self.messages[-1]["content"]
            self.messages[-1] = {
                "role": "assistant",
                "content": prefix_content,
                "prefix": True
            }

        return kwargs

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history"""
        self.messages.append({"role": role, "content": content}) 