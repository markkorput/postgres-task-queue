import pytest
from datetime import timedelta
from unittest.mock import AsyncMock
from pydantic import BaseModel

from postgres_task_queue.core.broker import Broker
from postgres_task_queue.core.queue import Queue, PydanticQueue, ArchiveOptions


class SimpleModel(BaseModel):
    name: str
    count: int


@pytest.fixture
def mock_broker():
    """Create a mock Broker for testing."""
    mock = AsyncMock(spec=Broker)
    mock.queue_name = "test_queue"
    return mock


class TestQueueBasics:
    """Tests for basic Queue functionality."""

    def test_queue_creation_with_defaults(self, mock_broker):
        queue = Queue(mock_broker)
        assert queue.broker.queue_name == "test_queue"
        assert queue.broker is mock_broker
        assert queue._archive_options is not None

    def test_queue_creation_with_archive_false(self, mock_broker):
        queue = Queue(mock_broker, archive=False)
        assert queue._archive_options is None

    def test_queue_creation_with_archive_dict(self, mock_broker):
        archive_opts: ArchiveOptions = {"ttl": timedelta(days=30), "limit": 1000}
        queue = Queue(mock_broker, archive=archive_opts)
        assert queue._archive_options == archive_opts

    def test_queue_creation_with_dlq_archive_false(self, mock_broker):
        queue = Queue(mock_broker, dlq_archive=False)
        assert queue._dlq_archive_options is None

    def test_queue_creation_with_dlq_archive_dict(self, mock_broker):
        dlq_archive_opts: ArchiveOptions = {"ttl": timedelta(days=7), "limit": 500}
        queue = Queue(mock_broker, dlq_archive=dlq_archive_opts)
        assert queue._dlq_archive_options == dlq_archive_opts


@pytest.mark.asyncio
class TestQueueEnqueue:
    """Tests for Queue.enqueue() method."""

    async def test_enqueue_calls_db_queue_send(self):
        """Test that enqueue calls broker.enqueue."""
        mock_broker = AsyncMock()
        queue = Queue(mock_broker)
        await queue.enqueue({"x": 42})
        mock_broker.enqueue.assert_called_once_with({"x": 42}, group=None)

    async def test_enqueue_with_dict(self):
        """Test that enqueue works with dict input."""
        mock_broker = AsyncMock()
        queue = Queue(mock_broker)
        await queue.enqueue({"key": "value"})
        mock_broker.enqueue.assert_called_once_with({"key": "value"}, group=None)


class TestPydanticQueue:
    @pytest.fixture
    def queue(self) -> PydanticQueue[SimpleModel]:
        mock_broker = AsyncMock()
        return PydanticQueue(mock_broker, SimpleModel)

    @pytest.mark.asyncio
    async def test_enqueue_with_model_instance_serializes(
        self, queue: PydanticQueue[SimpleModel]
    ):
        """Test that enqueue serializes pydantic models."""
        model_instance = SimpleModel(name="hello", count=42)
        await queue.enqueue(model_instance)
        queue.broker.enqueue.assert_called_once_with(  # ty: ignore
            {"name": "hello", "count": 42}, group=None
        )
