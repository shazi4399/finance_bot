"""Retry utilities with exponential backoff"""

import functools
from typing import Any, Callable

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def with_retry(max_attempts: int = 3, backoff_factor: float = 2.0, exceptions: tuple = (Exception,)):
    """Decorator for retry with exponential backoff"""

    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=backoff_factor, min=1, max=60),
            retry=retry_if_exception_type(exceptions),
            reraise=True,
        )
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return func(*args, **kwargs)

        return wrapper

    return decorator


class RetryableError(Exception):
    """Base class for retryable errors"""

    pass


class NetworkError(RetryableError):
    """Network-related retryable error"""

    pass


class APIError(RetryableError):
    """API-related retryable error"""

    pass
