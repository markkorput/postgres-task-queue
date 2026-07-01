from typing import Any, Callable, TypeVar, overload

from pydantic import BaseModel

from postgres_task_queue.pgmq.broker import PgmqBroker
from postgres_task_queue.core.queue import ArchiveOptions, Queue, PydanticQueue

InputType = TypeVar("InputType", bound=BaseModel)


@overload
def create_queue(
    name: str,
    input_model: None = None,
    *,
    archive: bool | ArchiveOptions = ...,
    dlq: str | bool = ...,
    dlq_archive: bool | ArchiveOptions = ...,
    group: Callable[[dict[str, Any]], str | None] | None = ...,
) -> Queue: ...


@overload
def create_queue(
    name: str,
    input_model: type[InputType],
    *,
    archive: bool | ArchiveOptions = ...,
    dlq: str | bool = ...,
    dlq_archive: bool | ArchiveOptions = ...,
    group: Callable[[InputType], str | None] | None = ...,
) -> PydanticQueue[InputType]: ...


def create_queue(
    name: str,
    input_model: type[InputType] | None = None,
    *,
    archive: bool | ArchiveOptions = True,
    dlq: str | bool = True,
    dlq_archive: bool | ArchiveOptions = True,
    group: Callable[[Any], str | None] | None = None,
) -> Queue | PydanticQueue[InputType]:
    """Create a Queue or PydanticQueue instance with a PgmqBroker.

    Args:
        name: The name of the queue.
        input_model: If provided, returns a PydanticQueue for this model type.
        archive: Archive options for the main queue (bool or ArchiveOptions dict).
        dlq: DLQ queue name (str) or whether to create a DLQ (bool). Defaults to True.
        dlq_archive: Archive options for the DLQ (bool or ArchiveOptions dict).
        group: Optional callable that takes the enqueue input and returns a group string.
               For Queue: Callable[[dict[str, Any]], str | None] | None
               For PydanticQueue: Callable[[InputType], str | None] | None

    Returns:
        A Queue instance if input_model is None, otherwise a PydanticQueue instance.
    """
    broker = PgmqBroker(
        queue_name=name,
        archive_table=archive if isinstance(archive, bool) else True,
        dlq_queue_name=dlq,
        dlq_archive_name=dlq_archive if isinstance(dlq_archive, bool) else True,
    )

    if input_model is None:
        return Queue(broker, archive=archive, dlq_archive=dlq_archive, group=group)
    else:
        return PydanticQueue(
            broker, input_model, archive=archive, dlq_archive=dlq_archive, group=group
        )
