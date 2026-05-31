from unittest.mock import AsyncMock

import pytest
from postgres_task_queue._broker import Broker, Task
from postgres_task_queue._processor import Processor
from postgres_task_queue._queue import Queue
from postgres_task_queue.worker import ProcessorWorker, Worker


@pytest.fixture
def broker():
    mock = AsyncMock(spec=Broker)
    mock.queue_name = "test_queue"
    return mock


@pytest.fixture
def processor(broker):
    queue = Queue(broker)

    async def dummy_processor(data: dict) -> None:
        pass

    return Processor(dummy_processor, queue)


@pytest.fixture
def processor_worker(processor):
    return ProcessorWorker(processor)


class TestProcessorWorker:
    """Tests for ProcessorWorker class."""

    @pytest.mark.asyncio
    async def test_poll_calls_broker_poll(self, processor_worker, broker):
        """ProcessorWorker.poll should call broker.poll with correct parameters."""
        broker.poll.return_value = (Task(id=1, payload={}),)

        result = await processor_worker.poll(batch_size=10)

        assert len(result) == 1
        broker.poll.assert_called_once()

    def test_should_prune_with_none_interval(self, processor_worker):
        """When prune_interval is None, should_prune should return False."""
        processor_worker.prune_interval = None
        processor_worker._next_prune_at = None
        assert processor_worker.should_prune() is False

    @pytest.mark.asyncio
    async def test_prune_calls_queue_prune(self, processor_worker, broker, processor):
        """ProcessorWorker.prune should call queue.prune with correct parameters."""
        processor.queue.prune = AsyncMock()
        processor_worker.prune_interval = None

        await processor_worker.prune()
        processor.queue.prune.assert_awaited_once()


class TestWorker:
    """Tests for Worker class."""

    def test_worker_initialization(self, processor):
        """Worker should initialize with correct parameters."""
        worker = Worker(
            processors={processor},
            concurrency_limit=5,
        )
        assert worker.processors == {processor}
        assert worker.concurrency_limit == 5
        assert worker.free_slots == 5

    def test_claim_slot_reduces_free_slots(self, processor):
        """_claim_slot should reduce free_slots by 1."""
        worker = Worker(processors={processor}, concurrency_limit=5)
        assert worker._claim_slot() is True
        assert worker.free_slots == 4

    def test_claim_slot_fails_when_no_slots(self, processor):
        """_claim_slot should return False when no slots available."""
        worker = Worker(processors={processor}, concurrency_limit=1)
        worker._claim_slot()
        assert worker._claim_slot() is False

    def test_free_slot_increases_free_slots(self, processor):
        """_free_slot should increase free_slots by 1."""
        worker = Worker(processors={processor}, concurrency_limit=5)
        worker._claim_slot()
        worker._free_slot()
        assert worker.free_slots == 5
