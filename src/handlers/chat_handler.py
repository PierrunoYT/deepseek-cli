"""Chat handler for DeepSeek CLI"""

import json
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich import box 
from rich.panel import Panel


# Simplified import handling with clear fallback chain
try:
    from deepseek_cli.config.settings import (
        MODEL_CONFIGS,
        TEMPERATURE_PRESETS,
        DEFAULT_MAX_TOKENS,
        DEFAULT_TEMPERATURE,
        MAX_FUNCTIONS,
        MAX_STOP_SEQUENCES,
        MAX_HISTORY_LENGTH
    )
    from deepseek_cli.utils.version_checker import check_version
except ImportError:
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
    def __init__(self, *, stream: bool = False) -> None:
        self.messages: List[Dict[str, Any]] = []
        self.model: str = "deepseek-chat"
        self.stream: bool = stream
        self.json_mode: bool = False
        self.max_tokens: int = DEFAULT_MAX_TOKENS
        self.functions: List[Dict[str, Any]] = []
        self.prefix_mode: bool = False
        self.temperature: float = DEFAULT_TEMPERATURE
        self.frequency_penalty: float = 0.0
        self.presence_penalty: float = 0.0
        self.top_p: float = 1.0
        self.stop_sequences: List[str] = []
        self.stream_options: Dict[str, bool] = {"include_usage": True}
        self.raw_mode: bool = False

        self.console = Console()

        # Check for new version with caching
        self._check_version_cached()

    def _check_version_cached(self) -> None:
        """Check for new version and cache the result"""
        try:
            update_available, current, latest = check_version()
            if update_available:
                self.console.print(f"\n[yellow]New version available: {latest} (current: {current})[/yellow]")
                self.console.print("[yellow]Update with: pip install --upgrade deepseek-cli[/yellow]\n")
        except Exception:
            pass  # Silently fail if version check fails

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
        kwargs: Dict[str, Any] = {
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

    def handle_response(self, response: Any) -> Optional[str]:
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
            self.console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
            return None

    def stream_response(self, response: Any) -> str:
        """Handle streaming response"""
        full_response: str = ""
        chunk_count = 0
        try:
            with Live("", console=self.console, refresh_per_second=8) as live:
                for chunk in response:
                    if hasattr(chunk.choices[0], 'delta'):
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content is not None:
                            content: str = delta.content
                            full_response += content
                            chunk_count += 1

                            # Update display every 3 chunks or if content ends with punctuation
                            # This reduces object creation while maintaining responsiveness
                            if chunk_count % 3 == 0 or content.rstrip().endswith(('.', '!', '?', '\n')):
                                bubble = Panel(
                                    Markdown(full_response),
                                    border_style="bright_blue",
                                    box=box.ROUNDED,
                                    padding=(0, 1),
                                    title="[bold green]AI[/bold green]"
                                )
                                live.update(bubble)

                # Final update to ensure complete response is displayed
                if full_response:
                    final_bubble = Panel(
                        Markdown(full_response),
                        border_style="bright_blue",
                        box=box.ROUNDED,
                        padding=(0, 1),
                        title="[bold green]AI[/bold green]"
                    )
                    live.update(final_bubble)

            if full_response:
                self.messages.append({
                    "role": "assistant",
                    "content": full_response
                })
            return full_response
        except Exception as e:
            self.console.print(f"\n[red]Error in stream response: {str(e)}[/red]")
            return full_response

    def display_token_info(self, usage: Dict[str, int]) -> None:
        """Display token usage information"""
        if usage:
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)

            # Estimate character counts (rough approximation)
            eng_chars = int(total_tokens * 0.75)   # 1 token ≈ 0.75 English chars
            cn_chars = int(total_tokens * 1.67)    # 1 token ≈ 1.67 Chinese chars

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

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history with limit"""
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > MAX_HISTORY_LENGTH:
            # Remove oldest messages but keep system message
            if self.messages[0]["role"] == "system":
                self.messages = [self.messages[0]] + self.messages[-(MAX_HISTORY_LENGTH-1):]
            else:
                self.messages = self.messages[-MAX_HISTORY_LENGTH:]
