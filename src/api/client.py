"""LiteLLM API client handler for multi-provider support"""

import os
from litellm import completion, acompletion
from typing import Dict, Any, List, Optional

# Simplified import handling with clear fallback chain
try:
    from deepseek_cli.config.settings import (
        DEFAULT_BASE_URL, 
        DEFAULT_BETA_URL,
        MODEL_CONFIGS,
        PROVIDER_API_KEYS,
        DEFAULT_MODEL
    )
    from deepseek_cli.utils.exceptions import DeepSeekError
except ImportError:
    from src.config.settings import (
        DEFAULT_BASE_URL,
        DEFAULT_BETA_URL,
        MODEL_CONFIGS,
        PROVIDER_API_KEYS,
        DEFAULT_MODEL
    )
    from src.utils.exceptions import DeepSeekError

class APIClient:
    def __init__(self, model: Optional[str] = None) -> None:
        """Initialize API client with LiteLLM
        
        Args:
            model: Optional model name to use (defaults to deepseek/deepseek-chat)
        """
        self.current_model = model or DEFAULT_MODEL
        self.beta_mode = False
        self.api_keys = self._load_api_keys()
        self._setup_environment()

    def _load_api_keys(self) -> Dict[str, Optional[str]]:
        """Load API keys from environment variables"""
        keys = {}
        for provider, env_var in PROVIDER_API_KEYS.items():
            if env_var:
                keys[provider] = os.getenv(env_var)
            else:
                keys[provider] = None  # For providers like Ollama that don't need keys
        return keys

    def _setup_environment(self) -> None:
        """Setup environment variables for LiteLLM"""
        # Set DeepSeek base URL for LiteLLM
        if self.beta_mode:
            os.environ["DEEPSEEK_API_BASE"] = DEFAULT_BETA_URL
        else:
            os.environ["DEEPSEEK_API_BASE"] = DEFAULT_BASE_URL
        
        # Set API keys in environment for LiteLLM
        for provider, env_var in PROVIDER_API_KEYS.items():
            if env_var and self.api_keys.get(provider):
                os.environ[env_var] = self.api_keys[provider]

    def get_provider_for_model(self, model: str) -> str:
        """Get the provider for a given model"""
        if model in MODEL_CONFIGS:
            return MODEL_CONFIGS[model].get("provider", "unknown")
        # Try to extract provider from model name (e.g., "deepseek/deepseek-chat")
        if "/" in model:
            return model.split("/")[0]
        return "unknown"

    def check_api_key(self, model: str) -> bool:
        """Check if API key is available for the model's provider"""
        provider = self.get_provider_for_model(model)
        
        # Ollama doesn't need an API key
        if provider == "ollama":
            return True
        
        env_var = PROVIDER_API_KEYS.get(provider)
        if not env_var:
            return True  # No key needed
        
        api_key = self.api_keys.get(provider)
        if not api_key:
            # Try to prompt for API key
            api_key = input(f"Please enter your {provider.upper()} API key: ").strip()
            if api_key:
                self.api_keys[provider] = api_key
                os.environ[env_var] = api_key
                return True
            return False
        return True

    def toggle_beta(self) -> None:
        """Toggle beta mode (only for DeepSeek models)"""
        self.beta_mode = not self.beta_mode
        self._setup_environment()

    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available models from configuration"""
        models = []
        for model_name, config in MODEL_CONFIGS.items():
            models.append({
                "name": model_name,
                "display_name": config.get("display_name", model_name),
                "provider": config.get("provider", "unknown"),
                "description": config.get("description", ""),
                "context_length": config.get("context_length", 0),
                "max_tokens": config.get("max_tokens", 0)
            })
        return models

    def list_models_by_provider(self, provider: str) -> List[Dict[str, Any]]:
        """List models for a specific provider"""
        return [
            {
                "name": model_name,
                "display_name": config.get("display_name", model_name),
                "description": config.get("description", "")
            }
            for model_name, config in MODEL_CONFIGS.items()
            if config.get("provider") == provider
        ]

    def create_chat_completion(self, **kwargs: Any) -> Any:
        """Create a chat completion using LiteLLM
        
        Args:
            **kwargs: Arguments to pass to the chat completion API
            
        Returns:
            Chat completion response
        """
        # Ensure model is specified
        if "model" not in kwargs:
            kwargs["model"] = self.current_model
        
        model = kwargs["model"]
        
        # Check if API key is available
        if not self.check_api_key(model):
            raise DeepSeekError(f"API key not available for {self.get_provider_for_model(model)}")
        
        # Convert functions to tools format if needed (for compatibility)
        if "functions" in kwargs:
            functions: List[Dict[str, Any]] = kwargs.pop("functions")
            kwargs["tools"] = [{"type": "function", "function": f} for f in functions]
        
        # Handle DeepSeek-specific parameters
        provider = self.get_provider_for_model(model)
        if provider == "deepseek":
            # Add custom base URL for DeepSeek
            if self.beta_mode:
                kwargs["api_base"] = DEFAULT_BETA_URL
            else:
                kwargs["api_base"] = DEFAULT_BASE_URL
        
        try:
            # Use LiteLLM's completion function
            response = completion(**kwargs)
            return response
        except Exception as e:
            raise DeepSeekError(f"Failed to create chat completion: {str(e)}")

    def update_api_key(self, provider: str, new_key: str) -> None:
        """Update API key for a specific provider
        
        Args:
            provider: The provider name (e.g., 'openai', 'anthropic')
            new_key: The new API key to use
        """
        if not new_key or not new_key.strip():
            raise DeepSeekError("API key cannot be empty")
        
        self.api_keys[provider] = new_key.strip()
        
        # Update environment variable
        env_var = PROVIDER_API_KEYS.get(provider)
        if env_var:
            os.environ[env_var] = new_key.strip()

    def set_model(self, model: str) -> bool:
        """Set the current model
        
        Args:
            model: Model name to use
            
        Returns:
            True if model is valid, False otherwise
        """
        if model in MODEL_CONFIGS:
            self.current_model = model
            return True
        return False

    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model
        
        Args:
            model: Model name
            
        Returns:
            Model configuration dictionary or None
        """
        return MODEL_CONFIGS.get(model)