"""Configuration settings for DeepSeek CLI"""

# API Information
API_CONTACT = "api-service@deepseek.com"
API_LICENSE = "MIT"
API_TERMS = "https://platform.deepseek.com/downloads/DeepSeek%20Open%20Platform%20Terms%20of%20Service.html"
API_AUTH_TYPE = "Bearer"
API_DOCS = "https://api-docs.deepseek.com/api/create-chat-completion"
API_BALANCE_ENDPOINT = "https://api-docs.deepseek.com/api/get-user-balance"

# API URLs
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_BETA_URL = "https://api.deepseek.com/beta"
ANTHROPIC_BASE_URL = "https://api.deepseek.com/anthropic"

# Feature configurations
FEATURE_CONFIGS = {
    "prefix_completion": {
        "requires_beta": True,
        "description": "Complete assistant messages from a given prefix"
    },
    "fim_completion": {
        "requires_beta": True,
        "max_tokens": 4096,
        "description": "Fill in the middle completion for content/code"
    },
    "json_mode": {
        "requires_json_word": True,
        "description": "Ensure model outputs valid JSON strings"
    },
    "context_cache": {
        "enabled_by_default": True,
        "min_cache_tokens": 64,
        "cache_hit_price_per_million": 0.014,  # $0.014 per million tokens
        "cache_miss_price_per_million": 0.14,  # $0.14 per million tokens
        "description": "Automatic context caching on disk for better performance and cost savings"
    }
}

# Model configurations with LiteLLM format
MODEL_CONFIGS = {
    # DeepSeek Models
    "deepseek/deepseek-chat": {
        "name": "deepseek/deepseek-chat",
        "display_name": "DeepSeek Chat",
        "provider": "deepseek",
        "version": "DeepSeek-V3.1",
        "mode": "Non-thinking Mode",
        "context_length": 128000,
        "max_tokens": 8192,
        "default_max_tokens": 4096,
        "description": "DeepSeek-V3.1 Chat model (Non-thinking Mode) with 128K context",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_streaming": True
    },
    "deepseek/deepseek-coder": {
        "name": "deepseek/deepseek-coder",
        "display_name": "DeepSeek Coder",
        "provider": "deepseek",
        "version": "DeepSeek-V2.5",
        "context_length": 128000,
        "max_tokens": 8192,
        "default_max_tokens": 4096,
        "description": "DeepSeek-V2.5 Coder model optimized for code generation",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_streaming": True
    },
    "deepseek/deepseek-reasoner": {
        "name": "deepseek/deepseek-reasoner",
        "display_name": "DeepSeek Reasoner",
        "provider": "deepseek",
        "version": "DeepSeek-V3.1",
        "mode": "Thinking Mode",
        "context_length": 128000,
        "max_tokens": 64000,
        "default_max_tokens": 32000,
        "description": "DeepSeek-V3.1 Reasoning model (Thinking Mode) with chain of thought",
        "supports_json": True,
        "supports_function_calling": False,
        "supports_streaming": True,
        "has_reasoning_content": True
    },
    # OpenAI Models
    "gpt-4o": {
        "name": "gpt-4o",
        "display_name": "GPT-4o",
        "provider": "openai",
        "context_length": 128000,
        "max_tokens": 16384,
        "default_max_tokens": 4096,
        "description": "OpenAI's most advanced multimodal model",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_streaming": True
    },
    "gpt-4o-mini": {
        "name": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "provider": "openai",
        "context_length": 128000,
        "max_tokens": 16384,
        "default_max_tokens": 4096,
        "description": "OpenAI's fast and affordable small model",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_streaming": True
    },
    "gpt-4-turbo": {
        "name": "gpt-4-turbo",
        "display_name": "GPT-4 Turbo",
        "provider": "openai",
        "context_length": 128000,
        "max_tokens": 4096,
        "default_max_tokens": 4096,
        "description": "OpenAI's GPT-4 Turbo model",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_streaming": True
    },
    # Anthropic Models
    "claude-3-5-sonnet-20241022": {
        "name": "claude-3-5-sonnet-20241022",
        "display_name": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "context_length": 200000,
        "max_tokens": 8192,
        "default_max_tokens": 4096,
        "description": "Anthropic's most intelligent model",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_streaming": True
    },
    "claude-3-5-haiku-20241022": {
        "name": "claude-3-5-haiku-20241022",
        "display_name": "Claude 3.5 Haiku",
        "provider": "anthropic",
        "context_length": 200000,
        "max_tokens": 8192,
        "default_max_tokens": 4096,
        "description": "Anthropic's fastest model",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_streaming": True
    },
    # Google Models
    "gemini/gemini-2.0-flash-exp": {
        "name": "gemini/gemini-2.0-flash-exp",
        "display_name": "Gemini 2.0 Flash",
        "provider": "gemini",
        "context_length": 1000000,
        "max_tokens": 8192,
        "default_max_tokens": 4096,
        "description": "Google's latest Gemini 2.0 Flash experimental model",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_streaming": True
    },
    "gemini/gemini-1.5-pro": {
        "name": "gemini/gemini-1.5-pro",
        "display_name": "Gemini 1.5 Pro",
        "provider": "gemini",
        "context_length": 2000000,
        "max_tokens": 8192,
        "default_max_tokens": 4096,
        "description": "Google's Gemini 1.5 Pro with 2M context",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_streaming": True
    },
    # Ollama (Local Models)
    "ollama/llama3.2": {
        "name": "ollama/llama3.2",
        "display_name": "Llama 3.2 (Local)",
        "provider": "ollama",
        "context_length": 128000,
        "max_tokens": 4096,
        "default_max_tokens": 2048,
        "description": "Meta's Llama 3.2 running locally via Ollama",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_streaming": True
    },
    "ollama/qwen2.5": {
        "name": "ollama/qwen2.5",
        "display_name": "Qwen 2.5 (Local)",
        "provider": "ollama",
        "context_length": 128000,
        "max_tokens": 4096,
        "default_max_tokens": 2048,
        "description": "Alibaba's Qwen 2.5 running locally via Ollama",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_streaming": True
    }
}

# Provider-specific API key environment variables
PROVIDER_API_KEYS = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "ollama": None  # No API key needed for local Ollama
}

# Default model
DEFAULT_MODEL = "deepseek/deepseek-chat"

# Temperature presets
TEMPERATURE_PRESETS = {
    "coding": 0.0,
    "data": 1.0,
    "chat": 1.3,
    "translation": 1.3,
    "creative": 1.5
}

# Default settings
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 1.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1
DEFAULT_MAX_RETRY_DELAY = 16

# API Limits
MAX_FUNCTIONS = 128
MAX_STOP_SEQUENCES = 16
MAX_HISTORY_LENGTH = 100