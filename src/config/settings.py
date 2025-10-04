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

# Model configurations
MODEL_CONFIGS = {
    "deepseek-chat": {
        "name": "deepseek-chat",
        "version": "DeepSeek-V3.1",
        "mode": "Non-thinking Mode",
        "context_length": 128000,  # 128K context
        "max_tokens": 8192,  # Default 4K, Maximum 8K
        "default_max_tokens": 4096,
        "description": "DeepSeek-V3.1 Chat model (Non-thinking Mode) with 128K context",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_prefix_completion": True,
        "supports_fim": True
    },
    "deepseek-coder": {
        "name": "deepseek-coder",
        "version": "DeepSeek-V2.5",
        "context_length": 128000,  # Assuming same as chat
        "max_tokens": 8192,  # Default 4K, Maximum 8K
        "default_max_tokens": 4096,
        "description": "DeepSeek-V2.5 Coder (merged with chat model, may be deprecated)",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_prefix_completion": True,
        "supports_fim": True,
        "note": "This model was merged into DeepSeek-V2.5 and may redirect to deepseek-chat"
    },
    "deepseek-reasoner": {
        "name": "deepseek-reasoner",
        "version": "DeepSeek-V3.1",
        "mode": "Thinking Mode",
        "context_length": 128000,  # 128K context
        "max_tokens": 64000,  # Default 32K, Maximum 64K
        "default_max_tokens": 32000,
        "description": "DeepSeek-V3.1 Reasoning model (Thinking Mode) with 128K context",
        "supports_json": True,
        "supports_function_calling": False,  # Not supported, falls back to deepseek-chat if tools provided
        "supports_prefix_completion": True,
        "supports_fim": False,
        "has_reasoning_content": True  # Special field for reasoning output
    }
}

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