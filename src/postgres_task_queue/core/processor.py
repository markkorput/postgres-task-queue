import asyncio
import logging
from typing import Any, Callable, Generic, TypeVar, cast, Awaitable

from pydantic import BaseModel

from .broker import Broker, Task
from .queue import PydanticQueue, Queue

logger = logging.getLogger(__name__)


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])
RetryPredicate = Callable[[Exception], bool]
RetrySpec = tuple[type[Exception], ...] | RetryPredicate | None
RetryDelaySpec = float | Callable[[int], float]
InputType = TypeVar("InputType", bound=BaseModel)


class Processor:
    """Simple processor that accepts dict input."""

    retry_delay: Callable[[int], float]
    timeout: int
    idempotency_key: str | None

    def __init__(
        self,
        fn: Callable[[dict[str, Any]], Awaitable[Any]],
        queue: Queue,
        *,
        concurrency_limit: int | None = None,
        max_retries: int = 0,
        retry_on: RetrySpec = None,
        retry_delay: RetryDelaySpec | None = None,
        timeout: int = 60,
        idempotency_key: str | None = None,
        grouped: bool = False,
        lifo: bool = False,
    ) -> None:
        self.fn = fn
        self.queue = queue
        self.concurrency_limit = concurrency_limit
        self.max_retries = max_retries
        self.retry_on = retry_on
        self.retry_delay = cast(
            Callable[[int], float],
            retry_delay if callable(retry_delay) else lambda _: retry_delay or 0.0,
        )
        self.timeout = timeout
        self.idempotency_key = idempotency_key
        self.grouped = grouped
        self.lifo = lifo

    async def __call__(self, input_data: dict[str, Any]) -> Any:
        return await self.fn(input_data)

    async def process(self, raw_input: dict[str, Any]) -> Any:
        """Receive and process input data from the queue."""
        return await self.fn(raw_input)

    @property
    def broker(self) -> Broker:
        return self.queue.broker

    def _should_retry_exception(self, exc: Exception) -> bool:
        """Determine if an exception should trigger a retry based on processor.retry_on."""
        retry_on = getattr(self, "retry_on", None)

        if retry_on is None:
            return True  # Default: retry on all exceptions

        if callable(retry_on):
            return retry_on(exc)

        if isinstance(retry_on, tuple):
            return any(isinstance(exc, e) for e in retry_on)

        return False

    async def process_task(self, task: Task) -> None:
        """
        Execute the processor with the received task's payload.

        If any exception is caught and this processor has a `dlq_queue_name`, then
        a DLQ item will be sent to that DLQ queue. The DLQ message will contain:
            - msg_id: id of the failed task
            - queue_name: the processor's queue_name
            - message: the payload of the failed task
            - error: the caught exception

        After the task processing is finished (regardless of success or exception),
        the original task is archived (if archive is enabled) or deleted (if archive is False).
        """
        logger.info(f"Process {repr(self.queue.broker.queue_name)} #{task.id}")

        # Respect queue-level concurrency-limit
        if limit := self.concurrency_limit:
            count = await self.broker.processing_count()
            # The tasks we just read also have vt, but we don't want
            # to count those, because they're not really active yet
            if count >= limit:
                logger.debug(
                    f"Concurrency limit reached for {self.queue.broker.queue_name}, skipping"
                )
                return

        # Set status to processing
        await self.broker.start(task.id)

        # Add idempotency key to payload if configured
        payload = task.payload
        if self.idempotency_key is not None:
            payload = {**payload, self.idempotency_key: str(task.id)}

        try:
            # Run processor logic with timeout. After the timeout, the processor will be cancelled and a Timeout
            # exception will be raised, which will be handled like any other exception
            await asyncio.wait_for(
                self.process(payload),
                timeout=self.timeout,
            )

            await self.broker.complete(task.id)
        except Exception as e:
            logger.exception(f"Processor processing exception: {e}")

            should_retry = self._should_retry_exception(e)

            await self.broker.fail(
                task.id,
                exc=e,
                max_retries=self.max_retries if should_retry else 0,
                delay_seconds=self.retry_delay,
            )

    async def poll(
        self,
        batch_size: int,
        poll_interval_ms: int = 1000,
        max_poll_seconds: int = 60,
    ) -> tuple[Task, ...]:
        """Poll for tasks from the processor's queue.

        When grouped=True, uses poll_grouped to maintain strict FIFO ordering
        within groups. Otherwise, uses regular poll.
        """
        poll_method = (
            self.queue.broker.poll_grouped if self.grouped else self.queue.broker.poll
        )
        return await poll_method(
            vt=self.timeout,
            qty=batch_size,
            max_poll_seconds=max_poll_seconds,
            poll_interval_ms=poll_interval_ms,
            lifo=self.lifo,
        )


class PydanticProcessor(Processor, Generic[InputType]):
    """A Processor that accepts a Pydantic BaseModel as input."""

    _pydantic_fn: Callable[[InputType], Awaitable[Any]]

    def __init__(
        self,
        fn: Callable[[InputType], Awaitable[Any]],
        queue: PydanticQueue[InputType],
        *,
        concurrency_limit: int | None = None,
        max_retries: int = 0,
        retry_on: RetrySpec = None,
        retry_delay: RetryDelaySpec | None = None,
        timeout: int = 60,
        idempotency_key: str | None = None,
        grouped: bool = False,
        lifo: bool = False,
    ) -> None:
        self._pydantic_fn = fn
        self.input_model = queue.input_model
        super().__init__(
            fn=self.process,
            queue=queue,
            concurrency_limit=concurrency_limit,
            max_retries=max_retries,
            retry_on=retry_on,
            retry_delay=retry_delay,
            timeout=timeout,
            idempotency_key=idempotency_key,
            grouped=grouped,
            lifo=lifo,
        )

    async def __call__(self, input_data: InputType) -> Any:  # ty: ignore
        """Invoke the processor with a Pydantic model.

        Converts the model to dict using model_dump() and calls
        the parent's __call__ with the dict.
        """
        return await super().__call__(input_data.model_dump())

    async def process(self, raw_input: dict[str, Any]) -> Any:
        """Receive and process input data from the queue.

        Converts the dict to InputType using model_validate and calls
        the pydantic function with the model instance.
        """
        # Validate input
        input_data = self.input_model.model_validate(raw_input)
        # Invoke original method
        return await self._pydantic_fn(input_data)
