from typing import Any, Callable, TypeVar, Awaitable, overload

from pydantic import BaseModel

from postgres_task_queue._processor import Processor, PydanticProcessor
from postgres_task_queue._queue import Queue, PydanticQueue

InputType = TypeVar("InputType", bound=BaseModel)


@overload
def processor(
    queue: PydanticQueue[InputType],
    *,
    concurrency_limit: int | None = ...,
    max_retries: int = ...,
    retry_on: tuple[type[Exception], ...] | Callable[[Exception], bool] | None = ...,
    retry_delay: float | Callable[[int], float] | None = ...,
    timeout: int = ...,
    idempotency_key: str | None = ...,
    lifo: bool = ...,
    grouped: bool = ...,
    poll_interval_ms: int = ...,
    max_poll_seconds: int = ...,
) -> Callable[
    [Callable[[InputType], Awaitable[Any]]], PydanticProcessor[InputType]
]: ...


@overload
def processor(
    queue: Queue,
    *,
    concurrency_limit: int | None = ...,
    max_retries: int = ...,
    retry_on: tuple[type[Exception], ...] | Callable[[Exception], bool] | None = ...,
    retry_delay: float | Callable[[int], float] | None = ...,
    timeout: int = ...,
    idempotency_key: str | None = ...,
    lifo: bool = ...,
    grouped: bool = ...,
) -> Callable[[Callable[[dict[str, Any]], Awaitable[Any]]], Processor]: ...


def processor(
    queue: Queue | PydanticQueue[InputType],
    **kwargs: Any,
) -> (
    Callable[[Callable[[dict[str, Any]], Awaitable[Any]]], Processor]
    | Callable[[Callable[[InputType], Awaitable[Any]]], PydanticProcessor[InputType]]
):
    """Decorator to create a Processor or PydanticProcessor instance.

    Args:
        queue: The queue instance (Queue or PydanticQueue).
        concurrency_limit: Maximum concurrent processing limit.
        max_retries: Maximum number of retry attempts.
        retry_on: Tuple of exception types or predicate to trigger retries.
        retry_delay: Delay in seconds or function to compute delay between retries.
        timeout: Processing timeout in seconds.
        idempotency_key: Field name to store the task ID for idempotency.
        grouped: When True, enables strict FIFO ordering within groups.
        poll_interval_ms: Interval in milliseconds between poll attempts.
        max_poll_seconds: Maximum time in seconds to wait for a message.

    Returns:
        A decorator that creates a Processor instance for regular Queue,
        or PydanticProcessor for PydanticQueue.
    """
    if isinstance(queue, PydanticQueue):

        def decorator(
            fn: Callable[[InputType], Awaitable[Any]],
        ) -> PydanticProcessor[InputType]:
            return PydanticProcessor(fn, queue, **kwargs)

    else:

        def decorator(fn: Callable[[dict[str, Any]], Awaitable[Any]]) -> Processor:
            return Processor(fn, queue, **kwargs)

    return decorator  # type: ignore[return-value]
