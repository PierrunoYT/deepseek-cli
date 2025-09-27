"""Configuration settings for DeepSeek CLI"""

# API Information
API_CONTACT = "api-service@deepseek.com"
API_LICENSE = "MIT"
API_TERMS = "https://platform.deepseek.com/downloads/DeepSeek%20Open%20Platform%20Terms%20of%20Service.html"
API_AUTH_TYPE = "Bearer"
API_DOCS = "https://api-docs.deepseek.com/api/create-chat-completion"
API_BALANCE_ENDPOINT = "https://api-docs.deepseek.com/api/get-user-balance"

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
        "description": "Automatic context caching for better performance"
    }
}

# Model configurations
MODEL_CONFIGS = {
    "deepseek-chat": {
        "name": "deepseek-chat",
        "max_tokens": 8192,
        "description": "DeepSeek-V2.5 Chat model with 8K token output limit"
    },
    "deepseek-coder": {
        "name": "deepseek-coder",
        "max_tokens": 8192,
        "description": "DeepSeek-V2.5 Coder model optimized for code generation"
    },
    "deepseek-reasoner": {
        "name": "deepseek-reasoner",
        "max_tokens": 8192,
        "description": "DeepSeek-R1 with 64K context and 8K output limit"
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
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_BETA_URL = "https://api.deepseek.com/beta"

# API Limits
MAX_FUNCTIONS = 128
MAX_STOP_SEQUENCES = 16
MAX_HISTORY_LENGTH = 100