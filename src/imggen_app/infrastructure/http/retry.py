import time
import logging
from typing import Callable, TypeVar, Any
import httpx
from imggen_app.domain.exceptions import SearchError, DownloadError

logger = logging.getLogger(__name__)

T = TypeVar("T")

def with_retry(
    max_attempts: int = 4,
    backoff_base: float = 0.8,
    retryable_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying HTTP requests with exponential backoff.
    Useful for handling rate limits (429) or transient server errors (5xx).
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except httpx.HTTPStatusError as e:
                    attempts += 1
                    if e.response.status_code in retryable_status_codes:
                        if attempts >= max_attempts:
                            raise
                        
                        wait_time = backoff_base * (2 ** (attempts - 1))
                        
                        # Respect Retry-After header
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            wait_time = max(wait_time, float(retry_after))
                            
                        logger.warning(
                            f"HTTP {e.response.status_code} error. "
                            f"Retrying in {wait_time:.2f}s (Attempt {attempts}/{max_attempts})..."
                        )
                        time.sleep(wait_time)
                    else:
                        raise
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        raise
                    
                    wait_time = backoff_base * (2 ** (attempts - 1))
                    logger.warning(
                        f"Network error: {e}. "
                        f"Retrying in {wait_time:.2f}s (Attempt {attempts}/{max_attempts})..."
                    )
                    time.sleep(wait_time)
            return func(*args, **kwargs) # Should not reach here
        return wrapper
    return decorator
