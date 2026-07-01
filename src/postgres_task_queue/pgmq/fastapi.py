from typing import Annotated, Self

from fastapi import APIRouter, HTTPException, Depends, Query, status

from pydantic import BaseModel

from postgres_task_queue.core.queue import Queue, ArchiveOptions
from .broker import Archive, Dlq, PgmqBroker, _Table


class ArchiveOptionsModel(BaseModel):
    """Model for queue archive options."""

    ttl: float | None = None
    limit: int | None = None

    @classmethod
    def from_options(cls, opts: ArchiveOptions) -> Self:
        """Convert ArchiveOptions to ArchiveOptionsModel, or None."""
        ttl = opts["ttl"].total_seconds() if "ttl" in opts else None
        limit = opts["limit"] if "limit" in opts else None

        return cls(ttl=ttl, limit=limit)


class DlqInfo(BaseModel):
    """Model for DLQ information."""

    name: str
    archive: ArchiveOptionsModel | None = None


class QueueInfo(BaseModel):
    """Model for queue information."""

    name: str
    archive: ArchiveOptionsModel | None = None
    dlq: DlqInfo | None = None

    @classmethod
    def from_queue(cls, queue: Queue) -> Self:
        broker = queue.broker

        return cls(
            name=broker.queue_name,
            archive=ArchiveOptionsModel.from_options(queue._archive_options)
            if queue._archive_options
            else None,
            dlq=DlqInfo(
                name=broker.dlq.queue_name,
                archive=ArchiveOptionsModel.from_options(queue._dlq_archive_options)
                if queue._dlq_archive_options
                else None,
            )
            if broker.dlq
            else None,
        )


class QueueItem(BaseModel):
    """Model for a queue item."""

    id: int
    payload: dict


class PaginatedItems(BaseModel):
    """Model for paginated items response."""

    items: list[QueueItem]
    page: int
    page_size: int
    total: int


def create_router(*queues: Queue) -> APIRouter:
    router = APIRouter()

    # Map queue names to Queue objects for quick lookup
    queue_map = {queue.broker.queue_name: queue for queue in queues}

    @router.get("/", response_model=list[QueueInfo])
    async def list_queues() -> list[QueueInfo]:
        return [QueueInfo.from_queue(queue) for queue in queues]

    def _get_queue(queue_name: str) -> Queue:
        """Selects the queue from the `queue_map` using the `queue_name` query param"""
        queue = queue_map.get(queue_name)

        if not queue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Queue {repr(queue_name)} not found",
            )

        return queue

    def _get_broker(
        queue: Annotated[Queue, Depends(_get_queue)],
    ) -> PgmqBroker:
        broker = queue.broker

        if isinstance(broker, PgmqBroker):
            return broker

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Queue {repr(queue.broker.queue_name)} does not have a PgmqBroker",
        )

    def _get_archive(
        broker: Annotated[PgmqBroker, Depends(_get_broker)],
    ) -> Archive:

        if broker.archive:
            return broker.archive

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Queue {repr(broker.queue_name)} does not have an archive",
        )

    def _get_dlq(
        broker: Annotated[PgmqBroker, Depends(_get_broker)],
    ) -> Dlq:

        if broker.dlq:
            return broker.dlq

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Queue {repr(broker.queue_name)} does not have a DLQ",
        )

    def _get_dlq_archive(
        broker: Annotated[PgmqBroker, Depends(_get_broker)],
    ) -> Archive:

        if broker.dlq and broker.dlq.archive:
            return broker.dlq.archive

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Queue {repr(broker.queue_name)} does not have a DLQ archive",
        )

    @router.get("/{queue_name}/queue", response_model=PaginatedItems)
    async def list_queue_items(
        broker: Annotated[PgmqBroker, Depends(_get_broker)],
        page: Annotated[int, Query(ge=1, description="Page number")] = 1,
        page_size: Annotated[
            int, Query(ge=1, le=1000, description="Items per page")
        ] = 100,
    ) -> PaginatedItems:
        """List items from a specific queue with pagination."""
        return await _list_items(
            broker,
            page=page,
            page_size=page_size,
        )

    @router.get("/{queue_name}/archive", response_model=PaginatedItems)
    async def list_archive_items(
        archive: Annotated[Archive, Depends(_get_archive)],
        page: Annotated[int, Query(ge=1, description="Page number")] = 1,
        page_size: Annotated[
            int, Query(ge=1, le=1000, description="Items per page")
        ] = 100,
    ) -> PaginatedItems:
        """List items from a specific queue-archive with pagination."""
        return await _list_items(
            archive,
            page=page,
            page_size=page_size,
        )

    @router.get("/{queue_name}/dlq", response_model=PaginatedItems)
    async def list_dlq_items(
        dlq: Annotated[Archive, Depends(_get_dlq)],
        page: Annotated[int, Query(ge=1, description="Page number")] = 1,
        page_size: Annotated[
            int, Query(ge=1, le=1000, description="Items per page")
        ] = 100,
    ) -> PaginatedItems:
        """List items from a specific DLQ with pagination."""
        return await _list_items(
            dlq,
            page=page,
            page_size=page_size,
        )

    @router.get("/{queue_name}/dlq/archive", response_model=PaginatedItems)
    async def list_dlq_archive_items(
        dlq_archive: Annotated[Archive, Depends(_get_dlq_archive)],
        page: Annotated[int, Query(ge=1, description="Page number")] = 1,
        page_size: Annotated[
            int, Query(ge=1, le=1000, description="Items per page")
        ] = 100,
    ) -> PaginatedItems:
        """List items from a specific DLQ-archive with pagination."""
        return await _list_items(
            dlq_archive,
            page=page,
            page_size=page_size,
        )

    async def _list_items(table: _Table, page: int, page_size: int):
        # Calculate offset from page and page_size
        offset = (page - 1) * page_size

        # Get total count first
        total = await table.count()

        # Then get items
        items_gen = table.items(offset=offset, limit=page_size)

        items = [
            QueueItem(id=task.id, payload=task.payload) async for task in items_gen
        ]

        return PaginatedItems(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
        )

    return router
