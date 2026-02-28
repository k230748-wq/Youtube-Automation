"""Retry utilities with exponential backoff."""

import functools
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = structlog.get_logger(__name__)


def with_retry(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 30,
    retry_on: tuple = (Exception,),
):
    """Decorator for retrying functions with exponential backoff."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retry_on),
        before_sleep=before_sleep_log(logger, "warning"),
        reraise=True,
    )


def retry_api_call(func):
    """Decorator specifically for API calls — retries on network/rate limit errors."""
    @functools.wraps(func)
    @with_retry(max_attempts=3, min_wait=2, max_wait=60)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
