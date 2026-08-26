"""Configuration settings for DeepSeek CLI"""

# API Information
API_CONTACT = "api-service@deepseek.com"
API_LICENSE = "MIT"
API_TERMS = "https://platform.deepseek.com/downloads/DeepSeek%20Open%20Platform%20Terms%20of%20Service.html"
API_AUTH_TYPE = "Bearer"
API_DOCS = "https://api-docs.deepseek.com/api/create-chat-completion"
API_BALANCE_ENDPOINT = "https://api-docs.deepseek.com/api/get-user-balance"

# API URLs
# The V4 announcement states the new models keep the existing base URLs and
# need only a model-parameter change, so the OpenAI-compatible /v1 path stays.
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
# Prefix completion and FIM are Beta-only features served from this host.
DEFAULT_BETA_URL = "https://api.deepseek.com/beta"

# Feature configurations
FEATURE_CONFIGS = {
    "prefix_completion": {
        "requires_beta": True,
        "description": "Complete assistant messages from a given prefix",
        "status": "beta",
    },
    "fim_completion": {
        "requires_beta": True,
        "max_tokens": 4096,  # "The max tokens of FIM completion is 4K."
        "description": "Fill in the middle completion for content/code",
        "status": "beta",
    },
    "json_mode": {
        "requires_json_word": True,
        "description": "Ensure model outputs valid JSON strings",
    },
    "context_cache": {
        "enabled_by_default": True,
        "min_cache_tokens": 64,
        "description": "Automatic context caching on disk for better performance and cost savings",
    },
}

# Model configurations.
#
# The V4 line replaced deepseek-chat / deepseek-reasoner / deepseek-coder,
# which were fully retired on 2026-07-24. Thinking is no longer a separate
# model: both v4-flash and v4-pro support Thinking and Non-thinking modes,
# selected per-request (see THINKING_* below).
MODEL_CONFIGS = {
    "deepseek-v4-flash": {
        "name": "deepseek-v4-flash",
        "version": "DeepSeek-V4-Flash",
        "context_length": 1_000_000,  # 1M context
        "max_tokens": 384_000,  # Maximum output tokens
        "default_max_tokens": 8192,
        "description": "DeepSeek-V4-Flash (284B total / 13B active) with 1M context",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_prefix_completion": True,
        "supports_fim": True,
        "supports_thinking": True,
        "supports_vision": False,
    },
    "deepseek-v4-pro": {
        "name": "deepseek-v4-pro",
        "version": "DeepSeek-V4-Pro",
        "context_length": 1_000_000,  # 1M context
        "max_tokens": 384_000,  # Maximum output tokens
        "default_max_tokens": 8192,
        "description": "DeepSeek-V4-Pro (1.6T total / 49B active) with 1M context",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_prefix_completion": True,
        "supports_fim": True,
        "supports_thinking": True,
        "supports_vision": False,
    },
    "deepseek-v4-flash-vision-exp": {
        "name": "deepseek-v4-flash-vision-exp",
        "version": "DeepSeek-V4-Flash-Vision (experimental)",
        "context_length": 1_000_000,  # 1M context
        "max_tokens": 384_000,  # Maximum output tokens
        "default_max_tokens": 8192,
        "description": "Experimental DeepSeek-V4-Flash variant with image input",
        "supports_json": True,
        "supports_function_calling": True,
        "supports_prefix_completion": True,
        "supports_fim": False,
        "supports_thinking": True,
        "supports_vision": True,
        "note": "Experimental. This CLI sends text only; images are not attached.",
    },
}

DEFAULT_MODEL = "deepseek-v4-flash"

# Model names retired on 2026-07-24. Kept only so a settings.json or a command
# written against an older release resolves to a working model with a warning
# instead of failing outright.
LEGACY_MODEL_ALIASES = {
    "deepseek-chat": "deepseek-v4-flash",
    "deepseek-reasoner": "deepseek-v4-flash",
    "deepseek-coder": "deepseek-v4-flash",
}

# Thinking (reasoning) mode. Enabled per-request via extra_body rather than by
# selecting a distinct model, and paired with a reasoning_effort level.
THINKING_EXTRA_BODY = {"thinking": {"type": "enabled"}}
REASONING_EFFORT_LEVELS = ("low", "high", "max")
DEFAULT_REASONING_EFFORT = "high"

# Parameters the API accepted historically but that are now ignored server-side.
# The CLI refuses to send them so the user is not misled into thinking they work.
DEPRECATED_SAMPLING_PARAMS = ("frequency_penalty", "presence_penalty")

# Temperature presets
TEMPERATURE_PRESETS = {
    "coding": 0.0,
    "data": 1.0,
    "chat": 1.3,
    "translation": 1.3,
    "creative": 1.5
}

# Default settings
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 1.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1
DEFAULT_MAX_RETRY_DELAY = 16

# API Limits
MAX_FUNCTIONS = 128
MAX_STOP_SEQUENCES = 16
MAX_HISTORY_LENGTH = 100
