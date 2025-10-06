"""DeepSeek API client handler"""

import os
import getpass
from openai import OpenAI
from typing import Dict, Any

# Add proper import paths for both development and installed modes
try:
    # When running as an installed package
    from config.settings import DEFAULT_BASE_URL, DEFAULT_BETA_URL
    from utils.exceptions import DeepSeekError
except ImportError:
    # When running in development mode
    from src.config.settings import DEFAULT_BASE_URL, DEFAULT_BETA_URL
    from src.utils.exceptions import DeepSeekError

class APIClient:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.client = self._create_client()
        self.beta_mode = False

    @staticmethod
    def _get_api_key() -> str:
        """Get API key from environment variable or secure prompt"""
        env_value = os.getenv("DEEPSEEK_API_KEY")
        if env_value and env_value.strip():
            return env_value.strip()

        # Fallback to secure, non-echoing prompt
        while True:
            api_key = getpass.getpass("Please enter your DeepSeek API key: ").strip()
            if api_key:
                return api_key

    def _create_client(self) -> OpenAI:
        """Create OpenAI client with DeepSeek configuration"""
        try:
            return OpenAI(
                api_key=self.api_key,
                base_url=DEFAULT_BASE_URL
            )
        except Exception as e:
            raise DeepSeekError(f"Failed to initialize API client: {str(e)}")

    def toggle_beta(self) -> None:
        """Toggle beta mode and update base URL"""
        self.beta_mode = not self.beta_mode
        self.client.base_url = DEFAULT_BETA_URL if self.beta_mode else DEFAULT_BASE_URL

    def list_models(self) -> Dict[str, Any]:
        """List available models"""
        return self.client.models.list()

    def create_chat_completion(self, **kwargs) -> Any:
        """Create a chat completion with proper function handling"""
        # Convert functions to tools format for compatibility
        if "functions" in kwargs:
            kwargs["tools"] = [{"type": "function", "function": f} for f in kwargs.pop("functions")]
        return self.client.chat.completions.create(**kwargs)

    def update_api_key(self, new_key: str) -> None:
        """Update API key and recreate client"""
        self.api_key = new_key
        self.client = self._create_client()