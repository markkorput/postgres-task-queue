from datetime import timedelta
from typing import Any, Callable, Generic, TypeVar, TypedDict

from pydantic import BaseModel

from .broker import Broker

InputType = TypeVar("InputType", bound=BaseModel)


class ArchiveOptions(TypedDict, total=False):
    ttl: timedelta
    limit: int


DEFAULT_ARCHIVE_OPTIONS: ArchiveOptions = {
    "ttl": timedelta(days=5 * 365),  # 5 years
    "limit": 1_000_000,
}


def _archive_options(opts: ArchiveOptions | bool) -> ArchiveOptions | None:
    if opts is True:
        return DEFAULT_ARCHIVE_OPTIONS

    if opts is False:
        return None

    return opts


class Queue:
    """High-level queue class that manages message enqueuing and rescheduling."""

    def __init__(
        self,
        broker: Broker,
        *,
        archive: bool | ArchiveOptions = True,
        dlq_archive: bool | ArchiveOptions = True,
        group: Callable[[dict[str, Any]], str | None] | None = None,
    ) -> None:
        self.broker = broker
        self._archive_options = _archive_options(archive)
        self._dlq_archive_options = _archive_options(dlq_archive)
        self._group_func = group

    async def enqueue(
        self, input_data: dict[str, Any], *, group: str | None = None
    ) -> None:
        """Enqueue a message to this queue."""
        if group is None and self._group_func:
            group = self._group_func(input_data)

        await self.broker.enqueue(input_data, group=group)

    async def reschedule(
        self,
        dlq_msg_id: int,
    ) -> int:
        return await self.broker.reschedule(dlq_msg_id)

    async def prune(self, *, batch_size: int = 1000) -> None:
        """
        Prune archived messages for this queue and its DLQ.

        Applies the archive configuration (ttl and limit) to both the main queue's
        archive and the DLQ's archive (if configured).
        """
        # Prune the main queue's archive if enabled
        if self._archive_options and self.broker.archive:
            await self.broker.archive.prune(
                ttl=self._archive_options.get("ttl"),
                limit=self._archive_options.get("limit"),
                batch_size=batch_size,
            )

        # Prune the DLQ's archive if enabled
        if self._dlq_archive_options and self.broker.dlq and self.broker.dlq.archive:
            await self.broker.dlq.archive.prune(
                ttl=self._dlq_archive_options.get("ttl"),
                limit=self._dlq_archive_options.get("limit"),
                batch_size=batch_size,
            )


class PydanticQueue(Queue, Generic[InputType]):
    """A Queue that accepts a Pydantic BaseModel as input."""

    input_model: type[InputType]
    _group_func: Callable[[InputType], str | None] | None

    def __init__(
        self,
        broker: Broker,
        input_model: type[InputType],
        *,
        archive: bool | ArchiveOptions = True,
        dlq_archive: bool | ArchiveOptions = True,
        group: Callable[[InputType], str | None] | None = None,
    ) -> None:
        super().__init__(broker, archive=archive, dlq_archive=dlq_archive)
        self.input_model = input_model
        self._group_func = group

    async def enqueue(self, input_data: InputType, *, group: str | None = None) -> None:  # ty: ignore
        """Enqueue a message to this queue.

        The input_data is serialized to a dict using model_dump() first.
        """
        if group is None and self._group_func:
            group = self._group_func(input_data)

        await super().enqueue(input_data.model_dump(), group=group)
