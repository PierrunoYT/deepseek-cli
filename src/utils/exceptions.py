"""Custom exceptions for DeepSeek CLI"""

class DeepSeekError(Exception):
    """Base exception class for DeepSeek CLI errors"""
    pass

class RateLimitExceeded(DeepSeekError):
    """Exception raised when API rate limit is exceeded"""
    pass 