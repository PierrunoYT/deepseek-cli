"""Error handler for DeepSeek CLI"""

import time
from typing import Optional, Dict, Any, Callable
from openai import APIError, RateLimitError

# Add proper import paths for both development and installed modes
try:
    # When running as an installed package
    from utils.exceptions import RateLimitExceeded
    from config.settings import DEFAULT_RETRY_DELAY, DEFAULT_MAX_RETRY_DELAY
except ImportError:
    # When running in development mode
    from src.utils.exceptions import RateLimitExceeded
    from src.config.settings import DEFAULT_RETRY_DELAY, DEFAULT_MAX_RETRY_DELAY

class ErrorHandler:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.retry_delay = DEFAULT_RETRY_DELAY
        self.max_retry_delay = DEFAULT_MAX_RETRY_DELAY

        # Define error messages for each status code
        self.status_messages = {
            400: {
                "message": "Bad request - check your input parameters",
                "solution": "Verify your request format and parameters"
            },
            401: {
                "message": "Authentication failed",
                "solution": "Check your API key or request new credentials"
            },
            403: {
                "message": "Forbidden - insufficient permissions",
                "solution": "Verify your account permissions and API key scope"
            },
            404: {
                "message": "Resource not found",
                "solution": "Check the requested endpoint or model name"
            },
            429: {
                "message": "Rate limit exceeded",
                "solution": "Please wait before making more requests"
            },
            500: {
                "message": "Internal server error",
                "solution": "Try again later or contact support"
            },
            503: {
                "message": "Service unavailable",
                "solution": "The service is temporarily unavailable, please try again later"
            }
        }

    def handle_error(self, e: APIError, api_client: Any = None) -> Optional[str]:
        """Handle API errors with detailed messages"""
        status_code = getattr(e, 'status_code', None)
        error_code = getattr(e, 'code', None)

        # Handle rate limit errors with retry
        if isinstance(e, RateLimitError) or status_code == 429:
            retry_after = int(getattr(e, 'headers', {}).get('retry-after', self.retry_delay))
            print(f"\nRate limit exceeded. Retrying in {retry_after} seconds...")
            time.sleep(retry_after)
            return "retry"

        # Handle other status codes
        if status_code in self.status_messages:
            error_info = self.status_messages[status_code]
            print(f"\nError ({status_code}): {error_info['message']}")
            print(f"Solution: {error_info['solution']}")

            # Special handling for specific error codes
            if status_code == 401 and api_client:
                # Prompt for new API key on authentication failure
                new_key = input("\nWould you like to enter a new API key? (y/n): ")
                if new_key.lower() == 'y':
                    api_client.update_api_key(input("Please enter your new DeepSeek API key: "))
                    return "retry"
            elif status_code in [500, 503]:
                # Offer automatic retry for server errors
                retry = input("\nWould you like to retry the request? (y/n): ")
                if retry.lower() == 'y':
                    return "retry"
        else:
            # Handle unknown errors
            print(f"\nUnexpected API Error (Code {status_code}): {str(e)}")
            if error_code:
                print(f"Error code: {error_code}")

        return None

    def retry_with_backoff(self, func: Callable, api_client: Any = None) -> Any:
        """Execute function with exponential backoff retry logic"""
        current_delay = self.retry_delay
        while True:
            try:
                return func()
            except Exception as e:
                result = self.handle_error(e, api_client)
                if result == "retry":
                    time.sleep(current_delay)
                    current_delay = min(current_delay * 2, self.max_retry_delay)
                    continue
                raise