"""Error handler for DeepSeek CLI"""

import time
from typing import Optional, Dict, Any, Callable
from openai import APIError, RateLimitError
from rich.console import Console

# Simplified import handling with clear fallback chain
try:
    from deepseek_cli.utils.exceptions import RateLimitExceeded
    from deepseek_cli.config.settings import DEFAULT_RETRY_DELAY, DEFAULT_MAX_RETRY_DELAY
except ImportError:
    from src.utils.exceptions import RateLimitExceeded
    from src.config.settings import DEFAULT_RETRY_DELAY, DEFAULT_MAX_RETRY_DELAY

class ErrorHandler:
    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self.retry_delay = DEFAULT_RETRY_DELAY
        self.max_retry_delay = DEFAULT_MAX_RETRY_DELAY
        self.console = Console()

        # Define error messages for each status code
        self.status_messages: Dict[int, Dict[str, str]] = {
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
        """Handle API errors with detailed messages
        
        Args:
            e: The API error to handle
            api_client: Optional API client for key updates
            
        Returns:
            Optional[str]: "retry" if the error should be retried, None otherwise
        """
        status_code = getattr(e, 'status_code', None)
        error_code = getattr(e, 'code', None)

        # Handle rate limit errors with retry
        if isinstance(e, RateLimitError) or status_code == 429:
            retry_after = int(getattr(e, 'headers', {}).get('retry-after', self.retry_delay))
            self.console.print(f"\n[yellow]Rate limit exceeded. Retrying in {retry_after} seconds...[/yellow]")
            time.sleep(retry_after)
            return "retry"

        # Handle other status codes
        if status_code in self.status_messages:
            error_info = self.status_messages[status_code]
            self.console.print(f"\n[red]Error ({status_code}): {error_info['message']}[/red]")
            self.console.print(f"[cyan]Solution: {error_info['solution']}[/cyan]")

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
            self.console.print(f"\n[red]Unexpected API Error (Code {status_code}): {str(e)}[/red]")
            if error_code:
                self.console.print(f"[red]Error code: {error_code}[/red]")

        return None

    def retry_with_backoff(self, func: Callable, api_client: Any = None) -> Any:
        """Execute function with exponential backoff retry logic
        
        Args:
            func: The function to execute with retry logic
            api_client: Optional API client for error handling
            
        Returns:
            Any: The result of the function call
            
        Raises:
            Exception: Re-raises the exception if max retries exceeded or error not retryable
        """
        current_delay = self.retry_delay
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                return func()
            except Exception as e:
                retry_count += 1
                result = self.handle_error(e, api_client)
                
                if result == "retry" and retry_count < self.max_retries:
                    self.console.print(f"[yellow]Retrying... ({retry_count}/{self.max_retries})[/yellow]")
                    time.sleep(current_delay)
                    current_delay = min(current_delay * 2, self.max_retry_delay)
                    continue
                else:
                    # Max retries reached or error not retryable
                    if retry_count >= self.max_retries:
                        self.console.print(f"[red]Max retries ({self.max_retries}) exceeded.[/red]")
                    raise
