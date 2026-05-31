from datetime import timedelta

import pytest
from unittest.mock import AsyncMock, patch

from pydantic import BaseModel

from postgres_task_queue.pgmq.queue import create_queue
from postgres_task_queue._queue import ArchiveOptions, PydanticQueue, Queue


class SampleModel(BaseModel):
    name: str
    value: int


class TestCreateQueue:
    """Tests for the create_queue factory function."""

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    def test_create_queue_returns_queue_when_no_input_model(self, mock_broker_class):
        """Test that create_queue returns a Queue when input_model is None."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        queue = create_queue("my_queue")

        assert isinstance(queue, Queue)
        assert not isinstance(queue, PydanticQueue)
        mock_broker_class.assert_called_once_with(
            queue_name="my_queue",
            archive_table=True,
            dlq_queue_name=True,
            dlq_archive_name=True,
        )

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    def test_create_queue_returns_pydantic_queue_when_input_model_given(
        self, mock_broker_class
    ):
        """Test that create_queue returns a PydanticQueue when input_model is provided."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        queue = create_queue("my_queue", input_model=SampleModel)

        assert isinstance(queue, PydanticQueue)
        mock_broker_class.assert_called_once_with(
            queue_name="my_queue",
            archive_table=True,
            dlq_queue_name=True,
            dlq_archive_name=True,
        )

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    def test_create_queue_with_archive_false(self, mock_broker_class):
        """Test that archive_table is False when archive=False."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        create_queue("my_queue", archive=False)

        call_kwargs = mock_broker_class.call_args[1]
        assert call_kwargs["archive_table"] is False

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    def test_create_queue_with_archive_dict(self, mock_broker_class):
        """Test that archive_table is True when archive is a dict."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        archive_opts: ArchiveOptions = {"ttl": timedelta(days=30), "limit": 1000}
        create_queue("my_queue", archive=archive_opts)

        call_kwargs = mock_broker_class.call_args[1]
        assert call_kwargs["archive_table"] is True

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    def test_create_queue_with_dlq_string(self, mock_broker_class):
        """Test that dlq_queue_name is set to custom string when dlq is a string."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        create_queue("my_queue", dlq="my_dlq")

        call_kwargs = mock_broker_class.call_args[1]
        assert call_kwargs["dlq_queue_name"] == "my_dlq"

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    def test_create_queue_with_dlq_false(self, mock_broker_class):
        """Test that dlq_queue_name is False when dlq=False."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        create_queue("my_queue", dlq=False)

        call_kwargs = mock_broker_class.call_args[1]
        assert call_kwargs["dlq_queue_name"] is False

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    def test_create_queue_with_dlq_archive_false(self, mock_broker_class):
        """Test that dlq_archive_name is False when dlq_archive=False."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        create_queue("my_queue", dlq_archive=False)

        call_kwargs = mock_broker_class.call_args[1]
        assert call_kwargs["dlq_archive_name"] is False

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    def test_create_queue_with_dlq_archive_dict(self, mock_broker_class):
        """Test that dlq_archive_name is True when dlq_archive is a dict."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        dlq_archive_opts: ArchiveOptions = {"ttl": timedelta(days=7), "limit": 500}
        create_queue("my_queue", dlq_archive=dlq_archive_opts)

        call_kwargs = mock_broker_class.call_args[1]
        assert call_kwargs["dlq_archive_name"] is True

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    def test_create_queue_passes_archive_to_queue(self, mock_broker_class):
        """Test that archive option is passed to the Queue constructor."""
        mock_broker = AsyncMock()
        mock_broker.queue_name = "my_queue"
        mock_broker.archive = None
        mock_broker.dlq = None
        mock_broker_class.return_value = mock_broker

        archive_opts: ArchiveOptions = {"ttl": timedelta(days=30), "limit": 1000}
        queue = create_queue("my_queue", archive=archive_opts)

        assert queue._archive_options == archive_opts

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    def test_create_queue_passes_dlq_archive_to_queue(self, mock_broker_class):
        """Test that dlq_archive option is passed to the Queue constructor."""
        mock_broker = AsyncMock()
        mock_broker.queue_name = "my_queue"
        mock_broker.archive = None
        mock_broker.dlq = None
        mock_broker_class.return_value = mock_broker

        dlq_archive_opts: ArchiveOptions = {"ttl": timedelta(days=7), "limit": 500}
        queue = create_queue("my_queue", dlq_archive=dlq_archive_opts)

        assert queue._dlq_archive_options == dlq_archive_opts

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    def test_create_queue_all_options(self, mock_broker_class):
        """Test create_queue with all options specified."""
        mock_broker = AsyncMock()
        mock_broker.queue_name = "my_queue"
        mock_broker.archive = None
        mock_broker.dlq = None
        mock_broker_class.return_value = mock_broker

        archive_opts: ArchiveOptions = {"ttl": timedelta(days=30), "limit": 1000}
        dlq_archive_opts: ArchiveOptions = {"ttl": timedelta(days=7), "limit": 500}

        queue = create_queue(
            "my_queue",
            input_model=SampleModel,
            archive=archive_opts,
            dlq="custom_dlq",
            dlq_archive=dlq_archive_opts,
        )

        assert isinstance(queue, PydanticQueue)
        assert queue._archive_options == archive_opts
        assert queue._dlq_archive_options == dlq_archive_opts

        call_kwargs = mock_broker_class.call_args[1]
        assert call_kwargs["queue_name"] == "my_queue"
        assert call_kwargs["archive_table"] is True
        assert call_kwargs["dlq_queue_name"] == "custom_dlq"
        assert call_kwargs["dlq_archive_name"] is True


@pytest.mark.asyncio
class TestQueueEnqueueGroup:
    """Tests for the group parameter in Queue and PydanticQueue enqueue methods."""

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    async def test_queue_enqueue_passes_group_to_broker(self, mock_broker_class):
        """Test that Queue.enqueue passes the group parameter to broker.enqueue."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        queue = Queue(mock_broker)
        await queue.enqueue({"task": "test"}, group="my-group")

        mock_broker.enqueue.assert_called_once_with({"task": "test"}, group="my-group")

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    async def test_queue_enqueue_without_group(self, mock_broker_class):
        """Test that Queue.enqueue works without group parameter."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        queue = Queue(mock_broker)
        await queue.enqueue({"task": "test"})

        mock_broker.enqueue.assert_called_once_with({"task": "test"}, group=None)

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    async def test_pydantic_queue_enqueue_passes_group_to_broker(
        self, mock_broker_class
    ):
        """Test that PydanticQueue.enqueue passes the group parameter to broker.enqueue."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        queue = PydanticQueue(mock_broker, SampleModel)
        sample = SampleModel(name="test", value=42)
        await queue.enqueue(sample, group="my-group")

        mock_broker.enqueue.assert_called_once_with(
            {"name": "test", "value": 42}, group="my-group"
        )

    @patch("postgres_task_queue.pgmq.queue.PgmqBroker")
    async def test_pydantic_queue_enqueue_without_group(self, mock_broker_class):
        """Test that PydanticQueue.enqueue works without group parameter."""
        mock_broker = AsyncMock()
        mock_broker_class.return_value = mock_broker

        queue = PydanticQueue(mock_broker, SampleModel)
        sample = SampleModel(name="test", value=42)
        await queue.enqueue(sample)

        mock_broker.enqueue.assert_called_once_with(
            {"name": "test", "value": 42}, group=None
        )
