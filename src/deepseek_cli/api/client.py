"""DeepSeek API client handler"""

import getpass
import os
import sys
from openai import OpenAI
from typing import Dict, Any, List

from deepseek_cli.config.settings import DEFAULT_BASE_URL, DEFAULT_BETA_URL
from deepseek_cli.utils.exceptions import DeepSeekError


class APIClient:
    def __init__(self) -> None:
        self.api_key = self._get_api_key()
        # Set before _create_client(), which reads it to pick the base URL.
        self.beta_mode = False
        self.client = self._create_client()

    @staticmethod
    def _prompt_secret(prompt: str) -> str:
        """Read a secret without echoing it to the terminal.

        Uses getpass so the key never lands in terminal scrollback or in the
        readline history buffer. Requires an interactive stdin; a non-TTY
        (piped/redirected) invocation raises rather than blocking forever.
        """
        if not sys.stdin.isatty():
            raise DeepSeekError(
                "No API key available and stdin is not a terminal. "
                "Set the DEEPSEEK_API_KEY environment variable."
            )
        try:
            return getpass.getpass(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            raise DeepSeekError("API key entry cancelled")

    @classmethod
    def _get_api_key(cls) -> str:
        """Get API key from environment variable or prompt user"""
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            api_key = cls._prompt_secret("Please enter your DeepSeek API key: ")
            if not api_key:
                raise DeepSeekError("API key cannot be empty")
        return api_key

    def _create_client(self) -> OpenAI:
        """Create OpenAI client with DeepSeek configuration"""
        try:
            base_url = DEFAULT_BETA_URL if self.beta_mode else DEFAULT_BASE_URL
            return OpenAI(
                api_key=self.api_key,
                base_url=base_url
            )
        except Exception as e:
            raise DeepSeekError(f"Failed to initialize API client: {str(e)}")

    def toggle_beta(self) -> None:
        """Toggle beta mode and update base URL"""
        self.beta_mode = not self.beta_mode
        self.client.base_url = DEFAULT_BETA_URL if self.beta_mode else DEFAULT_BASE_URL

    def list_models(self) -> Dict[str, Any]:
        """List available models"""
        try:
            return self.client.models.list()
        except Exception as e:
            raise DeepSeekError(f"Failed to list models: {str(e)}")

    def create_chat_completion(self, **kwargs: Any) -> Any:
        """Create a chat completion with proper function handling

        Args:
            **kwargs: Arguments to pass to the chat completion API

        Returns:
            Chat completion response
        """
        # Convert functions to tools format for compatibility
        if "functions" in kwargs:
            functions: List[Dict[str, Any]] = kwargs.pop("functions")
            kwargs["tools"] = [{"type": "function", "function": f} for f in functions]

        # Let SDK exceptions propagate directly so callers can inspect
        # status_code, headers, code, etc. (APIError, RateLimitError, …)
        return self.client.chat.completions.create(**kwargs)

    def update_api_key(self, new_key: str) -> None:
        """Update API key and recreate client

        Args:
            new_key: The new API key to use
        """
        if not new_key or not new_key.strip():
            raise DeepSeekError("API key cannot be empty")
        self.api_key = new_key.strip()
        self.client = self._create_client()

    def prompt_for_new_api_key(self) -> None:
        """Interactively read a replacement API key and rebuild the client."""
        self.update_api_key(self._prompt_secret("Please enter your new DeepSeek API key: "))
