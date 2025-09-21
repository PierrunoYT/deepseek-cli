"""Chat handler for DeepSeek CLI"""

import json
import time
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich import box 
from rich.panel import Panel


# Add proper import paths for both development and installed modes
try:
    # When running as an installed package
    from config.settings import (
        MODEL_CONFIGS,
        TEMPERATURE_PRESETS,
        DEFAULT_MAX_TOKENS,
        DEFAULT_TEMPERATURE,
        MAX_FUNCTIONS,
        MAX_STOP_SEQUENCES,
        MAX_HISTORY_LENGTH
    )
    from utils.version_checker import check_version
except ImportError:
    # When running in development mode
    from src.config.settings import (
        MODEL_CONFIGS,
        TEMPERATURE_PRESETS,
        DEFAULT_MAX_TOKENS,
        DEFAULT_TEMPERATURE,
        MAX_FUNCTIONS,
        MAX_STOP_SEQUENCES,
        MAX_HISTORY_LENGTH
    )
    from src.utils.version_checker import check_version

class ChatHandler:
    def __init__(self, *, stream: bool = True):
        self.messages = []
        self.model = "deepseek-chat"
        self.stream = stream
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

        self.console = Console()

        # Streaming output configuration - adjustable as needed
        self.stream_config = {
            "buffer_size_chars": 50,      # Buffer size character threshold
            "buffer_size_tokens": 15,     # Buffer size token threshold
            "time_threshold": 0.2,        # Time refresh threshold (seconds)
            "max_visible_chars": 8000,    # Maximum visible characters
            "scroll_buffer": 1000,        # Scroll buffer
            "refresh_rate": 8,            # Live refresh rate
            "min_buffer_for_sentence": 20, # Minimum buffer for sentence end check
            "min_buffer_for_time": 10,    # Minimum buffer for time threshold check
            "min_buffer_for_pause": 30,   # Minimum buffer for pause marker check
        }

        # Check for new version
        update_available, current_version, latest_version = check_version()
        if update_available:
            print(f"\n📦 Update available: v{current_version} → v{latest_version}")
            print("To update, run: pip install --upgrade deepseek-cli")
            print("For development installation: pip install -e . --upgrade\n")

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
            "max_tokens": self.max_tokens
        }

        # Only add these parameters if not using the reasoner model
        if self.model != "deepseek-reasoner":
            kwargs.update({
                "temperature": self.temperature,
                "frequency_penalty": self.frequency_penalty,
                "presence_penalty": self.presence_penalty,
                "top_p": self.top_p
            })

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

    def handle_response(self, response) -> Optional[str]:
        """Handle API response and extract content"""
        try:
            if not self.stream:
                if hasattr(response, 'usage'):
                    self.display_token_info(response.usage.model_dump())

                # Get the message from the response
                choice = response.choices[0]
                if not hasattr(choice, 'message'):
                    return None

                message = choice.message
                content = message.content if hasattr(message, 'content') else None

                # Handle tool calls (function calling)
                if hasattr(message, "tool_calls") and message.tool_calls:
                    tool_calls = []
                    for tool_call in message.tool_calls:
                        if tool_call.type == "function":
                            tool_calls.append({
                                "id": tool_call.id,
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            })
                    return json.dumps(tool_calls, indent=2)

                # Handle regular message content
                if content is not None:
                    self.messages.append({
                        "role": "assistant",
                        "content": content
                    })
                    self.console.print(Panel(
                                Markdown(content),
                                border_style="bright_blue",
                                box=box.ROUNDED,
                                padding=(0, 1),
                                title="[bold green]AI[/bold green]"
                            ))
                    return content
            
                return None
            else:
                return self.stream_response(response)
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            return None

    def stream_response(self, response: Any) -> str:
        """Handle streaming response with intelligent buffer and refresh strategy"""
        full_response: str = ""
        buffer: str = ""  # Buffer for collecting data packs
        
        config = self.stream_config
        BUFFER_SIZE_CHARS = config["buffer_size_chars"]
        TIME_THRESHOLD = config["time_threshold"] 
        MAX_VISIBLE_CHARS = config["max_visible_chars"]
        SCROLL_BUFFER = config["scroll_buffer"]
        REFRESH_RATE = config["refresh_rate"]
        
        SENTENCE_ENDS = ('.', '!', '?', '\n', '。', '！', '？')  # Sentence ending markers
        PAUSE_INDICATORS = (',', ';', '，', '；', '\n')        # Pause markers
        
        chunk_count = 0
        last_update_time = time.time()
        
        try:
            with Live("", console=self.console, refresh_per_second=REFRESH_RATE) as live:
                for chunk in response:
                    if hasattr(chunk.choices[0], 'delta'):
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content is not None:
                            content: str = delta.content
                            full_response += content
                            buffer += content  # Add to buffer
                            chunk_count += 1
                            current_time = time.time()   # Find the first sentence boundary as the starting point
                            
                            buffer_length = len(buffer)
                            time_since_last_update = current_time - last_update_time
                            response_length = len(full_response)
                            
                            should_refresh = False
                            refresh_reason = ""
                            
                            # Condition 1: Buffer reaches character threshold
                            if buffer_length >= BUFFER_SIZE_CHARS:
                                should_refresh = True
                                refresh_reason = "buffer_size"
                            
                            # Condition 2: Buffer contains sentence ending markers and has enough content
                            elif (buffer_length >= config["min_buffer_for_sentence"] and 
                                  any(char in buffer for char in SENTENCE_ENDS)):
                                should_refresh = True
                                refresh_reason = "sentence_end"
                            
                            # Condition 3: Time threshold reached and has content
                            elif (time_since_last_update >= TIME_THRESHOLD and 
                                  buffer_length >= config["min_buffer_for_time"]):
                                should_refresh = True
                                refresh_reason = "time_threshold"
                            
                            # Condition 4: Buffer contains pause markers and has enough content
                            elif (buffer_length >= config["min_buffer_for_pause"] and 
                                  any(char in buffer[-5:] for char in PAUSE_INDICATORS)):
                                should_refresh = True
                                refresh_reason = "pause_indicator"
                            
                            # Condition 5: Force refresh - avoid buffer becoming too large
                            elif buffer_length >= BUFFER_SIZE_CHARS * 2:
                                should_refresh = True
                                refresh_reason = "force_refresh"
                            
                            if should_refresh:
                                # Intelligent display content (avoid truncation, use scrolling window)
                                display_content = self._prepare_display_content(
                                    full_response, response_length, MAX_VISIBLE_CHARS, SCROLL_BUFFER
                                )
                                
                                bubble = Panel(
                                    Markdown(display_content),
                                    border_style="bright_blue",
                                    box=box.ROUNDED,
                                    padding=(0, 1),
                                    title=f"[bold green]AI[/bold green] [dim]({refresh_reason})[/dim]"
                                )
                                live.update(bubble)
                                
                                # Reset buffer and time
                                buffer = ""
                                last_update_time = current_time

                if full_response:
                    display_content = self._prepare_final_display_content(
                        full_response, MAX_VISIBLE_CHARS
                    )
                    
                    final_bubble = Panel(
                        Markdown(display_content),
                        border_style="bright_blue",
                        box=box.ROUNDED,
                        padding=(0, 1),
                        title="[bold green]AI[/bold green] [dim](complete)[/dim]"
                    )
                    live.update(final_bubble)
                    
            if full_response:
                self.messages.append({
                    "role": "assistant",
                    "content": full_response
                })
            return full_response
        except Exception as e:
            self.console.print(f"\nError in stream response: {str(e)}")
            return full_response
    
    def _prepare_display_content(self, full_response: str, response_length: int, 
                                max_visible_chars: int, scroll_buffer: int) -> str:
        """Prepare content to display with intelligent scrolling"""
        if response_length <= max_visible_chars:
            return full_response
        
        truncate_start = response_length - max_visible_chars + scroll_buffer
        truncate_content = full_response[truncate_start:]
        
        sentence_ends = ('.', '!', '?', '\n', '。', '！', '？')
        for i, char in enumerate(truncate_content[:200]):  # Search within first 200 characters
            if char in sentence_ends:
                truncate_content = truncate_content[i+1:].lstrip()
                break
        
        return "...\n\n" + truncate_content
    
    def _prepare_final_display_content(self, full_response: str, max_visible_chars: int) -> str:
        """Prepare final display content with intelligent handling of overly long content"""
        if len(full_response) <= max_visible_chars:
            return full_response
        
        start_part = full_response[:2000]
        end_part = full_response[-(max_visible_chars-2200):]
        
        sentence_ends = ('.', '!', '?', '\n', '。', '！', '？')
        
        for i in range(len(start_part)-1, max(len(start_part)-200, 0), -1):
            if start_part[i] in sentence_ends:
                start_part = start_part[:i+1]
                break
        
        for i, char in enumerate(end_part[:200]):
            if char in sentence_ends:
                end_part = end_part[i+1:].lstrip()
                break
        
        return start_part + "\n\n...[Content too long, some parts omitted]...\n\n" + end_part

    def display_token_info(self, usage: dict) -> None:
        """Display token usage information"""
        if usage:
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)

            # Estimate character counts (rough approximation)
            eng_chars = total_tokens * 0.75   # 1 token ≈ 0.75 English chars
            cn_chars = total_tokens * 1.67    # 1 token ≈ 1.67 Chinese chars

            # Compose text
            text = (
                f"[bold yellow]Token Usage:[/bold yellow]\n"
                f"  [green]Input tokens:[/green] {input_tokens}\n"
                f"  [green]Output tokens:[/green] {output_tokens}\n"
                f"  [green]Total tokens:[/green] {total_tokens}\n\n"
                f"[bold yellow]Estimated character equivalents:[/bold yellow]\n"
                f"  [cyan]English:[/cyan] ~{eng_chars} characters\n"
                f"  [cyan]Chinese:[/cyan] ~{cn_chars} characters"
            )

            # Print in a nice box
            self.console.print(Panel(text, title="Token Info", border_style="cyan", box=box.ROUNDED))
    def configure_stream_settings(self, **kwargs) -> Dict[str, Any]:
        """
        Dynamically configure streaming output settings
        
        Configurable parameters:
        - buffer_size_chars: Buffer character threshold (default: 50)
        - time_threshold: Time refresh threshold in seconds (default: 0.2)
        - max_visible_chars: Maximum visible characters (default: 8000)
        - refresh_rate: Live refresh rate (default: 8)
        
        Returns current configuration
        """
        valid_keys = {
            "buffer_size_chars", "buffer_size_tokens", "time_threshold",
            "max_visible_chars", "scroll_buffer", "refresh_rate",
            "min_buffer_for_sentence", "min_buffer_for_time", "min_buffer_for_pause"
        }
        
        updated = {}
        for key, value in kwargs.items():
            if key in valid_keys:
                self.stream_config[key] = value
                updated[key] = value
        
        return {
            "updated": updated,
            "current_config": self.stream_config.copy()
        }

    def get_stream_settings(self) -> Dict[str, Any]:
        """Get current streaming output configuration"""
        return self.stream_config.copy()

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history with limit"""
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > MAX_HISTORY_LENGTH:
            # Remove oldest messages but keep system message
            if self.messages[0]["role"] == "system":
                self.messages = [self.messages[0]] + self.messages[-(MAX_HISTORY_LENGTH-1):]
            else:
                self.messages = self.messages[-MAX_HISTORY_LENGTH:]
