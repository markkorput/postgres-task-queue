from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable, Protocol, runtime_checkable


@dataclass
class Task:
    """Represents a task/message from the queue."""

    id: int
    payload: dict[str, Any]


@runtime_checkable
class Archive(Protocol):
    """Protocol for queue archive implementations."""

    async def prune(
        self,
        *,
        ttl: timedelta | None = None,
        limit: int | None = None,
        batch_size: int = 1000,
    ) -> int:
        """Delete archived messages based on TTL or limit."""
        ...


@runtime_checkable
class Dlq(Protocol):
    """Protocol for dead letter queue implementations."""

    @property
    def queue_name(self) -> str:
        """The name of the DLQ."""
        ...

    @property
    def archive(self) -> Archive | None:
        """The archive table for this DLQ, or None if not configured."""
        ...

    async def enqueue(
        self,
        payload: dict[str, Any],
        *,
        group: str | None = None,
    ) -> Any:
        """Enqueue a message to the DLQ."""
        ...


@runtime_checkable
class Broker(Protocol):
    """Protocol for message broker implementations."""

    @property
    def queue_name(self) -> str:
        """The name of the queue."""
        ...

    @property
    def archive(self) -> Archive | None:
        """The archive table for this queue, or None if not configured."""
        ...

    @property
    def dlq(self) -> Dlq | None:
        """The dead letter queue for this queue, or None if not configured."""
        ...

    async def enqueue(
        self,
        payload: dict[str, Any],
        *,
        group: str | None = None,
    ) -> Any:
        """Enqueue a message to the queue."""
        ...

    async def poll(
        self,
        vt: int = 30,
        qty: int = 1,
        max_poll_seconds: int = 5,
        poll_interval_ms: int = 100,
        lifo: bool = False,
    ) -> tuple[Task, ...]:
        """Poll for messages from the queue."""
        ...

    async def poll_grouped(
        self,
        vt: int = 30,
        qty: int = 1,
        max_poll_seconds: int = 5,
        poll_interval_ms: int = 100,
        lifo: bool = False,
    ) -> tuple[Task, ...]:
        """Poll for messages from the queue with strict group ordering.

        When using grouped polling, messages are returned in FIFO order
        within each group, ensuring strict ordering within groups.
        """
        ...

    async def processing_count(self) -> int:
        """Count the number of active (in-progress) messages in the queue."""
        ...

    async def reschedule(
        self,
        dlq_msg_id: int,
    ) -> int:
        """Reschedule a message from the DLQ back to the main queue."""
        ...

    async def start(self, msg_id: int) -> None:
        """Mark a message as started/processing."""
        ...

    async def complete(self, msg_id: int) -> None:
        """Mark a message as completed and remove it from the queue."""
        ...

    async def fail(
        self,
        msg_id: int,
        exc: Exception,
        *,
        max_retries: int = 0,
        delay_seconds: Callable[[int], float] | float = 0.0,
    ) -> None:
        """Mark a message as failed, potentially retrying or sending to DLQ."""
        ...

    async def count(self) -> int:
        """Count the total number of items in the queue."""
        ...
