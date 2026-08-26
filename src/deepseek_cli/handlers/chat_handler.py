"Chat handler for DeepSeek CLI"

import json
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich import box 
from rich.panel import Panel


from deepseek_cli.config.settings import (
    MODEL_CONFIGS,
    DEFAULT_MODEL,
    LEGACY_MODEL_ALIASES,
    TEMPERATURE_PRESETS,
    THINKING_EXTRA_BODY,
    REASONING_EFFORT_LEVELS,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    MAX_FUNCTIONS,
    MAX_STOP_SEQUENCES,
    MAX_HISTORY_LENGTH,
)
from deepseek_cli.utils.version_checker import check_version
from deepseek_cli.utils.persistence import PersistenceManager

# Fill-in-the-Middle input markers and the API's hard 4K output cap for FIM.
FIM_PREFIX_TAG = "<fim_prefix>"
FIM_SUFFIX_TAG = "<fim_suffix>"
FIM_PREFIX_CLOSE = "</fim_prefix>"
FIM_SUFFIX_CLOSE = "</fim_suffix>"
FIM_MAX_TOKENS = 4096

class ChatHandler:
    def __init__(self, *, stream: bool = False) -> None:
        self.messages: List[Dict[str, Any]] = []
        self.model: str = DEFAULT_MODEL
        self.stream: bool = stream
        self.json_mode: bool = False
        self.max_tokens: int = MODEL_CONFIGS[DEFAULT_MODEL].get(
            "default_max_tokens", DEFAULT_MAX_TOKENS
        )
        self.functions: List[Dict[str, Any]] = []
        self.prefix_mode: bool = False
        self.fim_mode: bool = False
        # Thinking mode is a per-request parameter on the V4 models, not a
        # separate model name as it was for deepseek-reasoner.
        self.thinking: bool = False
        self.reasoning_effort: str = DEFAULT_REASONING_EFFORT
        self.temperature: float = DEFAULT_TEMPERATURE
        self.top_p: float = 1.0
        self.stop_sequences: List[str] = []
        self.stream_options: Dict[str, bool] = {"include_usage": True}
        self.raw_mode: bool = False

        self.console = Console()
        
        # Initialize persistence manager
        self.persistence = PersistenceManager()

        # Check for new version with caching
        self._check_version_cached()
        
        # Load previous history and settings
        self._load_persisted_data()

    def _check_version_cached(self) -> None:
        """Check for a new version, hitting PyPI at most once per TTL window."""
        try:
            cache_file = self.persistence.get_data_dir() / "version_check.json"
            update_available, current, latest = check_version(cache_file=cache_file)
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
        # Save settings after change
        self.save_state()

    def toggle_stream(self) -> None:
        """Toggle streaming mode"""
        self.stream = not self.stream

    @staticmethod
    def resolve_model(model: str) -> Optional[str]:
        """Map *model* to a currently-served model id, or None if unknown.

        Accepts the retired deepseek-chat / deepseek-reasoner / deepseek-coder
        names and resolves them to their V4 replacement so older saved
        settings keep working.
        """
        if model in MODEL_CONFIGS:
            return model
        return LEGACY_MODEL_ALIASES.get(model)

    def switch_model(self, model: str) -> bool:
        """Switch between available models"""
        resolved = self.resolve_model(model)
        if resolved is None:
            return False
        if resolved != model:
            self.console.print(
                f"[yellow]'{model}' was retired on 2026-07-24; "
                f"using '{resolved}' instead.[/yellow]"
            )
        self.model = resolved
        self.max_tokens = MODEL_CONFIGS[resolved].get("default_max_tokens", DEFAULT_MAX_TOKENS)
        # Save settings after change
        self.save_state()
        return True

    def set_max_tokens(self, value: int) -> bool:
        """Set the output token cap, bounded by the current model's maximum."""
        limit = MODEL_CONFIGS[self.model].get("max_tokens", DEFAULT_MAX_TOKENS)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            return False
        if value > limit:
            return False
        self.max_tokens = value
        self.save_state()
        return True

    def toggle_thinking(self) -> None:
        """Toggle Thinking mode (reasoning) for the current model."""
        self.thinking = not self.thinking
        self.save_state()

    def set_reasoning_effort(self, effort: str) -> bool:
        """Set the reasoning effort level used when Thinking mode is on."""
        effort = effort.strip().lower()
        if effort not in REASONING_EFFORT_LEVELS:
            return False
        self.reasoning_effort = effort
        self.save_state()
        return True

    def model_supports(self, capability: str) -> bool:
        """True when the current model advertises *capability*."""
        return bool(MODEL_CONFIGS.get(self.model, {}).get(capability, False))


    def get_current_provider(self) -> str:
        """Get the provider of the current model"""
        return "deepseek"

    def set_temperature(self, temp_str: str) -> bool:
        """Set temperature either by number or preset name"""
        try:
            # Try to parse as float first
            temp = float(temp_str)
            if 0 <= temp <= 2:
                self.temperature = temp
                # Save settings after change
                self.save_state()
                return True
            return False
        except ValueError:
            # Try as preset name
            preset = temp_str.lower()
            if preset in TEMPERATURE_PRESETS:
                self.temperature = TEMPERATURE_PRESETS[preset]
                # Save settings after change
                self.save_state()
                return True
            return False

    def set_top_p(self, top_p: float) -> bool:
        """Set top_p between 0.0 and 1.0"""
        if 0.0 <= top_p <= 1.0:
            self.top_p = top_p
            # Save settings after change
            self.save_state()
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
        """Prepare chat completion request parameters.
        
        Does NOT mutate self.messages — prefix mode injects a read-only view
        into the messages list passed to the API, leaving history intact.
        """
        # Build the message list for the request.  For prefix mode the last
        # user message is presented as an assistant prefix WITHOUT modifying
        # self.messages so retries and history remain consistent.
        if self.prefix_mode and self.messages and self.messages[-1]["role"] == "user":
            messages = list(self.messages[:-1]) + [{
                "role": "assistant",
                "content": self.messages[-1]["content"],
                "prefix": True
            }]
        else:
            messages = self.messages

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": self.stream,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }

        # frequency_penalty / presence_penalty are deliberately never sent:
        # the API documents them as no longer supported and ignores them.

        if self.json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        if self.functions:
            kwargs["tools"] = [{"type": "function", "function": f} for f in self.functions]

        # Thinking mode is requested per-request on the V4 models rather than
        # by switching to a dedicated reasoning model.
        if self.thinking and self.model_supports("supports_thinking"):
            kwargs["extra_body"] = dict(THINKING_EXTRA_BODY)
            kwargs["reasoning_effort"] = self.reasoning_effort

        if self.stop_sequences:
            kwargs["stop"] = self.stop_sequences

        if self.stream:
            kwargs["stream_options"] = self.stream_options

        return kwargs

    @staticmethod
    def parse_fim_input(text: str) -> tuple:
        """Split FIM input into (prefix, suffix).

        Accepts the documented tag form::

            <fim_prefix>def f():\\n<fim_suffix>    return x

        The ``<fim_prefix>`` tag is optional. When no ``<fim_suffix>`` tag is
        present the whole input is the prefix and there is no suffix, which
        makes FIM behave like a plain completion.
        """
        body = text
        # Closing tags are optional; accept and discard them so both the
        # <a>x</a><b>y</b> and <a>x<b>y spellings work.
        for closing in (FIM_PREFIX_CLOSE, FIM_SUFFIX_CLOSE):
            body = body.replace(closing, "")
        if FIM_PREFIX_TAG in body:
            body = body.split(FIM_PREFIX_TAG, 1)[1]
        if FIM_SUFFIX_TAG in body:
            prefix, suffix = body.split(FIM_SUFFIX_TAG, 1)
            return prefix, suffix
        return body, None

    def prepare_fim_request(self, prefix: str, suffix: Optional[str]) -> Dict[str, Any]:
        """Build kwargs for a Fill-in-the-Middle completion request."""
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "prompt": prefix,
            # FIM output is capped at 4K regardless of the model's chat limit.
            "max_tokens": min(self.max_tokens, FIM_MAX_TOKENS),
            "stream": self.stream,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        if suffix is not None:
            kwargs["suffix"] = suffix
        if self.stop_sequences:
            kwargs["stop"] = self.stop_sequences
        if self.stream:
            kwargs["stream_options"] = self.stream_options
        return kwargs

    def handle_completion_response(self, response: Any) -> Optional[str]:
        """Render a FIM/text-completion response (choices[].text, not .message)."""
        try:
            if self.stream:
                text = ""
                for chunk in response:
                    if not getattr(chunk, "choices", None):
                        continue
                    piece = getattr(chunk.choices[0], "text", None)
                    if piece:
                        text += piece
                        self.console.print(piece, end="")
                if text:
                    self.console.print()
                return text

            usage = getattr(response, "usage", None)
            if usage is not None and not self.raw_mode:
                self.display_token_info(usage.model_dump())
            if not getattr(response, "choices", None):
                return None
            text = getattr(response.choices[0], "text", None)
            if text is None:
                return None
            self.console.print(Panel(
                Markdown(f"```\n{text}\n```"),
                border_style="bright_blue",
                box=box.ROUNDED,
                padding=(0, 1),
                title="[bold green]FIM Completion[/bold green]",
            ))
            return text
        except Exception as e:
            self.console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
            return None

    def handle_response(self, response: Any) -> Optional[str]:
        """Handle API response and extract content"""
        try:
            if not self.stream:
                # hasattr() is True even when usage is None, which used to
                # raise AttributeError and discard an otherwise good response.
                usage = getattr(response, 'usage', None)
                if usage is not None and not self.raw_mode:
                    self.display_token_info(usage.model_dump())

                # Get the message from the response
                if not getattr(response, 'choices', None):
                    return None
                choice = response.choices[0]
                if not hasattr(choice, 'message'):
                    return None

                message = choice.message
                content = message.content if hasattr(message, 'content') else None
                
                # Handle reasoning content emitted in Thinking mode
                reasoning_content = None
                if hasattr(message, 'reasoning_content') and message.reasoning_content:
                    reasoning_content = message.reasoning_content
                    if not self.raw_mode:
                        self.console.print(Panel(
                            Markdown(f"**Reasoning Process:**\n\n{reasoning_content}"),
                            border_style="yellow",
                            box=box.ROUNDED,
                            padding=(0, 1),
                            title="[bold yellow]Chain of Thought[/bold yellow]"
                        ))

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
                    rendered = json.dumps(tool_calls, indent=2)
                    # Record the turn so the conversation does not desync from
                    # what the model actually produced.
                    assistant_msg: Dict[str, Any] = {
                        "role": "assistant",
                        "content": content or "",
                        "tool_calls": tool_calls,
                    }
                    # The API requires reasoning_content to be echoed back on
                    # every subsequent request once tool calls are in play;
                    # omitting it returns a 400.
                    if reasoning_content:
                        assistant_msg["reasoning_content"] = reasoning_content
                    self.messages.append(assistant_msg)
                    return rendered

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
        reasoning_content: str = ""
        usage: Any = None
        chunk_count = 0
        try:
            with Live("", console=self.console, refresh_per_second=8) as live:
                for chunk in response:
                    # The final chunk emitted when stream_options.include_usage
                    # is set carries the usage payload and an EMPTY choices
                    # list. Indexing it unconditionally raised IndexError and
                    # aborted the loop before the reply was ever recorded.
                    chunk_usage = getattr(chunk, 'usage', None)
                    if chunk_usage is not None:
                        usage = chunk_usage
                    if not getattr(chunk, 'choices', None):
                        continue

                    if hasattr(chunk.choices[0], 'delta'):
                        delta = chunk.choices[0].delta

                        # Handle reasoning content emitted in Thinking mode
                        if hasattr(delta, 'reasoning_content') and delta.reasoning_content is not None:
                            reasoning_content += delta.reasoning_content
                            if not self.raw_mode:
                                reasoning_bubble = Panel(
                                    Markdown(f"**Reasoning Process:**\n\n{reasoning_content}"),
                                    border_style="yellow",
                                    box=box.ROUNDED,
                                    padding=(0, 1),
                                    title="[bold yellow]Chain of Thought[/bold yellow]"
                                )
                                live.update(reasoning_bubble)
                        
                        # Handle regular content
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

            if usage is not None and not self.raw_mode:
                self.display_token_info(usage.model_dump())
            return full_response
        except Exception as e:
            self.console.print(f"\n[red]Error in stream response: {str(e)}[/red]")
            return full_response
        finally:
            # Record whatever was received even if the stream was interrupted
            # part-way, so history always matches what the user was shown.
            if full_response:
                self.messages.append({
                    "role": "assistant",
                    "content": full_response
                })

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
        
        # Auto-save after adding messages
        self.save_state()
    
    def _load_persisted_data(self) -> None:
        """Load persisted history and settings"""
        # Load history, keeping only well-formed messages. Anything else on
        # disk would surface later as a TypeError in /history or a 400 from
        # the API.
        loaded_messages = self.persistence.load_history()
        if loaded_messages:
            self.messages = [
                m for m in loaded_messages
                if isinstance(m, dict)
                and isinstance(m.get("role"), str)
                and isinstance(m.get("content"), str)
            ]


        # Load settings
        loaded_settings = self.persistence.load_settings()
        if loaded_settings:
            self._apply_loaded_settings(loaded_settings)
    
    @staticmethod
    def _coerce_number(value: Any, low: float, high: float) -> Optional[float]:
        """Return *value* as a float inside [low, high], or None if it isn't.

        bool is rejected explicitly because it is a subclass of int and would
        otherwise silently become 0.0/1.0.
        """
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        number = float(value)
        if number != number:  # NaN never compares inside a range
            return None
        return number if low <= number <= high else None

    def _apply_loaded_settings(self, settings: Dict[str, Any]) -> None:
        """Apply loaded settings to current state.

        The settings file is on-disk state that another local process (or a
        corrupted write) can influence, so every field is validated to the
        same type/range the interactive setters enforce. Invalid entries are
        dropped rather than propagated into an API request.
        """
        if not isinstance(settings, dict):
            return

        # resolve_model() also accepts the retired deepseek-chat / -reasoner /
        # -coder names that older versions of this CLI wrote here.
        saved_model = settings.get("model")
        resolved = self.resolve_model(saved_model) if isinstance(saved_model, str) else None
        if resolved is not None:
            self.model = resolved
            self.max_tokens = MODEL_CONFIGS[resolved].get("default_max_tokens", DEFAULT_MAX_TOKENS)

        for key, low, high in (
            ("temperature", 0.0, 2.0),
            ("top_p", 0.0, 1.0),
        ):
            if key in settings:
                number = self._coerce_number(settings[key], low, high)
                if number is not None:
                    setattr(self, key, number)

        for key in ("json_mode", "prefix_mode", "fim_mode", "thinking"):
            if isinstance(settings.get(key), bool):
                setattr(self, key, settings[key])

        if settings.get("reasoning_effort") in REASONING_EFFORT_LEVELS:
            self.reasoning_effort = settings["reasoning_effort"]

        max_tokens = settings.get("max_tokens")
        if isinstance(max_tokens, int) and not isinstance(max_tokens, bool):
            limit = MODEL_CONFIGS[self.model].get("max_tokens", DEFAULT_MAX_TOKENS)
            if 1 <= max_tokens <= limit:
                self.max_tokens = max_tokens

        stop_sequences = settings.get("stop_sequences")
        if isinstance(stop_sequences, list):
            self.stop_sequences = [
                s for s in stop_sequences if isinstance(s, str)
            ][:MAX_STOP_SEQUENCES]

        functions = settings.get("functions")
        if isinstance(functions, list):
            self.functions = [
                f for f in functions if isinstance(f, dict)
            ][:MAX_FUNCTIONS]


    def get_current_settings(self) -> Dict[str, Any]:
        """Get current settings as a dictionary"""
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "json_mode": self.json_mode,
            "prefix_mode": self.prefix_mode,
            "fim_mode": self.fim_mode,
            "thinking": self.thinking,
            "reasoning_effort": self.reasoning_effort,
            "stop_sequences": self.stop_sequences,
            "functions": self.functions
        }
    
    def save_state(self) -> bool:
        """Save current history and settings to disk"""
        history_success = self.persistence.save_history(self.messages)
        settings_success = self.persistence.save_settings(self.get_current_settings())
        return history_success and settings_success
    
    def clear_persisted_data(self) -> bool:
        """Clear all persisted data from disk"""
        history_success = self.persistence.clear_history()
        settings_success = self.persistence.clear_settings()
        return history_success and settings_success