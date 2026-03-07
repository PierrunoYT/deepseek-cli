"""Error handler for DeepSeek CLI"""

import time
from typing import Optional, Dict, Any, Callable
from openai import APIError, RateLimitError, AuthenticationError
from rich.console import Console

# Simplified import handling with clear fallback chain
try:
    # When installed via pip/pipx (package_dir={"": "src"})
    from utils.exceptions import RateLimitExceeded
    from config.settings import DEFAULT_RETRY_DELAY, DEFAULT_MAX_RETRY_DELAY
except ImportError:
    # When running from source (development mode)
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

    def handle_error(self, e: Exception, api_client: Any = None) -> Optional[str]:
        """Handle API errors with detailed messages, preserving SDK error metadata.
        
        Args:
            e: The exception to handle (APIError subclasses or generic Exception)
            api_client: Optional API client for key updates
            
        Returns:
            Optional[str]: "retry" if the error should be retried, None otherwise
        """
        # Preserve SDK metadata: status_code, code, headers are available on APIError
        status_code = getattr(e, 'status_code', None)
        error_code = getattr(e, 'code', None)

        # Handle rate limit errors — sleep is already done by handle_error, so
        # retry_with_backoff must NOT add another sleep on top for this case.
        if isinstance(e, RateLimitError) or status_code == 429:
            retry_after = self.retry_delay
            raw_headers = getattr(e, 'headers', None) or {}
            header_val = raw_headers.get('retry-after') if hasattr(raw_headers, 'get') else None
            if header_val is not None:
                try:
                    retry_after = int(header_val)
                except (ValueError, TypeError):
                    pass
            self.console.print(f"\n[yellow]Rate limit exceeded. Retrying in {retry_after} seconds...[/yellow]")
            time.sleep(retry_after)
            return "retry"

        # Handle authentication errors with optional key recovery
        if isinstance(e, AuthenticationError) or status_code == 401:
            error_info = self.status_messages.get(401, {})
            self.console.print(f"\n[red]Error (401): {error_info.get('message', 'Authentication failed')}[/red]")
            self.console.print(f"[cyan]Solution: {error_info.get('solution', 'Check your API key')}[/cyan]")
            if api_client:
                new_key = input("\nWould you like to enter a new API key? (y/n): ")
                if new_key.lower() == 'y':
                    api_client.update_api_key(input("Please enter your new DeepSeek API key: "))
                    return "retry"
            return None

        # Handle other known status codes
        if status_code in self.status_messages:
            error_info = self.status_messages[status_code]
            self.console.print(f"\n[red]Error ({status_code}): {error_info['message']}[/red]")
            self.console.print(f"[cyan]Solution: {error_info['solution']}[/cyan]")

            if status_code in [500, 503]:
                retry = input("\nWould you like to retry the request? (y/n): ")
                if retry.lower() == 'y':
                    return "retry"
        else:
            # Unknown / non-API errors — preserve as much detail as possible
            self.console.print(f"\n[red]Unexpected error (status={status_code}): {str(e)}[/red]")
            if error_code:
                self.console.print(f"[red]Error code: {error_code}[/red]")

        return None

    def retry_with_backoff(self, func: Callable, api_client: Any = None) -> Any:
        """Execute function with exponential backoff retry logic.
        
        Rate-limit waits are handled inside handle_error; other retries (401
        key recovery, 5xx user-confirmed retries) use the backoff delay here.
        
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
                    # For rate-limit errors the sleep already happened in handle_error;
                    # for other retryable errors apply exponential backoff here.
                    if not isinstance(e, RateLimitError) and getattr(e, 'status_code', None) != 429:
                        time.sleep(current_delay)
                        current_delay = min(current_delay * 2, self.max_retry_delay)
                    continue
                else:
                    if retry_count >= self.max_retries:
                        self.console.print(f"[red]Max retries ({self.max_retries}) exceeded.[/red]")
                    raise
