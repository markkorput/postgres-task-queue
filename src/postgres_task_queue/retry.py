"""Pre-built retry delay strategies for use with Processor(retry_delay=...)."""

from typing import Callable


def fixed(seconds: float) -> Callable[[int], float]:
    """Fixed delay strategy. Returns a callable that always returns the same delay in seconds.

    Usage:
        my_task = Processor(my_task_fn, queue, max_retries=3, retry_delay=retry.fixed(5.0))
    """
    return lambda _: seconds


def linear(seconds_per_attempt: float) -> Callable[[int], float]:
    """Linear backoff strategy. Delay increases linearly with attempt number.

    Args:
        seconds_per_attempt: Number of seconds to add per attempt (multiplier).

    Returns:
        A callable that takes attempt number (1-based) and returns delay in seconds.

    Usage:
        my_task = Processor(my_task_fn, queue, max_retries=3, retry_delay=retry.linear(10))
        # 10s, 20s, 30s
    """
    return lambda n: n * seconds_per_attempt


def exponential(
    base: float = 2.0,
    max_delay: float | None = None,
) -> Callable[[int], float]:
    """Exponential backoff strategy. Delay grows exponentially with attempt number.

    Args:
        base: Base multiplier for exponential growth (default: 2.0).
        max_delay: Maximum delay in seconds (None for no cap).

    Returns:
        A callable that takes attempt number (1-based) and returns delay in seconds.

    Usage:
        my_task = Processor(my_task_fn, queue, max_retries=5, retry_delay=retry.exponential(max_delay=300))
        # 2s, 4s, 8s, 16s, 32s (capped at 300s)

        my_task = Processor(my_task_fn, queue, max_retries=3, retry_delay=retry.exponential(base=1.5, max_delay=60))
        # ~1.5s, ~2.25s, ~3.375s (capped at 60s)
    """

    def strategy(n: int) -> float:
        delay = base**n
        if max_delay is not None:
            return min(delay, max_delay)
        return delay

    return strategy
