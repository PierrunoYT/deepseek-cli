"""Error handler for DeepSeek CLI"""

import time
from typing import Optional, Dict, Any, Callable
from openai import APIError, RateLimitError
from ..utils.exceptions import RateLimitExceeded
from ..config.settings import DEFAULT_RETRY_DELAY, DEFAULT_MAX_RETRY_DELAY

class ErrorHandler:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.retry_delay = DEFAULT_RETRY_DELAY
        self.max_retry_delay = DEFAULT_MAX_RETRY_DELAY
        
        # Define error messages for each status code
        self.status_messages = {
            400: {
                "message": "Invalid request body format.",
                "solution": "Please modify your request body according to the hints in the error message."
            },
            401: {
                "message": "Authentication fails due to the wrong API key.",
                "solution": "Please check your API key or create a new one if needed."
            },
            402: {
                "message": "Insufficient balance in your account.",
                "solution": "Please check your account balance and top up if needed."
            },
            422: {
                "message": "Invalid parameters in the request.",
                "solution": "Please modify your request parameters according to the error message."
            },
            429: {
                "message": "Rate limit reached - too many requests.",
                "solution": "Please pace your requests. Consider retrying after a brief wait."
            },
            500: {
                "message": "Server error occurred.",
                "solution": "Please retry your request after a brief wait. Contact support if the issue persists."
            },
            503: {
                "message": "Server is currently overloaded.",
                "solution": "Please retry your request after a brief wait."
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

    def retry_with_backoff(self, func: Callable, api_client: Any = None, *args, **kwargs) -> Optional[Any]:
        """Execute function with exponential backoff retry"""
        current_delay = self.retry_delay
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except APIError as e:
                if attempt == self.max_retries - 1:
                    # On last attempt, just handle the error without retry
                    self.handle_error(e, api_client)
                    return None
                
                result = self.handle_error(e, api_client)
                if result == "retry":
                    retry_after = int(getattr(e, 'headers', {}).get('retry-after', current_delay))
                    print(f"\nRetry attempt {attempt + 1}/{self.max_retries} in {retry_after} seconds...")
                    time.sleep(retry_after)
                    current_delay = min(current_delay * 2, self.max_retry_delay)
                    continue
                return None
            except Exception as e:
                print(f"\nUnexpected error: {str(e)}")
                return None
        return None 