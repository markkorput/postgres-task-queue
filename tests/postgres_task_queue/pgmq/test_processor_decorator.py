import pytest
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from pydantic import BaseModel, ValidationError

from postgres_task_queue._processor import Processor, PydanticProcessor
from postgres_task_queue.pgmq.processor import processor
from postgres_task_queue._queue import PydanticQueue

if TYPE_CHECKING:
    from postgres_task_queue._broker import Broker


class SimpleModel(BaseModel):
    name: str
    count: int


@pytest.fixture
def mock_queue() -> "Broker":
    """Create a mock Broker for testing."""
    mock = AsyncMock()
    mock.queue_name = "test_queue"
    return mock


class TestProcessorDecorator:
    """Tests for the processor decorator."""

    def test_processor_decorator_returns_processor_for_queue(self, mock_queue):
        """Test that processor decorator returns a Processor for a regular Queue."""

        @processor(mock_queue)
        async def handle_dict(data: dict) -> str:
            return f"{data['name']}: {data['count']}"

        assert isinstance(handle_dict, Processor)
        assert handle_dict.queue == mock_queue

    def test_processor_decorator_returns_pydantic_processor_for_pydantic_queue(
        self, mock_queue
    ):
        """Test that processor decorator returns a PydanticProcessor for a PydanticQueue."""
        queue = PydanticQueue(mock_queue, SimpleModel)

        @processor(queue)
        async def handle_model(data: SimpleModel) -> str:
            return f"{data.name}: {data.count}"

        assert isinstance(handle_model, PydanticProcessor)
        assert handle_model.queue == queue
        assert handle_model.input_model is SimpleModel

    def test_processor_decorator_passes_options(self, mock_queue):
        """Test that processor decorator passes all options to the processor."""
        queue: PydanticQueue[SimpleModel] = PydanticQueue(mock_queue, SimpleModel)

        @processor(
            queue,
            concurrency_limit=10,
            max_retries=3,
            timeout=120,
            idempotency_key="task_id",
        )
        async def handle_model(data: SimpleModel) -> str:
            return f"{data.name}: {data.count}"

        assert handle_model.concurrency_limit == 10
        assert handle_model.max_retries == 3
        assert handle_model.timeout == 120
        assert handle_model.idempotency_key == "task_id"

    @pytest.mark.asyncio
    async def test_processor_decorator_with_queue_processes_dict(self, mock_queue):
        """Test that decorated processor with Queue processes dict input."""

        @processor(mock_queue)
        async def handle_dict(data: dict) -> str:
            return f"{data['name']}: {data['count']}"

        result = await handle_dict.process({"name": "test", "count": 5})
        assert result == "test: 5"

    @pytest.mark.asyncio
    async def test_processor_decorator_with_pydantic_queue_validates_input(
        self, mock_queue
    ):
        """Test that decorated processor with PydanticQueue validates input."""
        queue: PydanticQueue[SimpleModel] = PydanticQueue(mock_queue, SimpleModel)

        @processor(queue)
        async def handle_model(data: SimpleModel) -> str:
            return f"{data.name}: {data.count}"

        processed = await handle_model.process({"name": "test", "count": 5})
        assert processed == "test: 5"

    @pytest.mark.asyncio
    async def test_processor_decorator_with_pydantic_queue_raises_validation_error(
        self, mock_queue
    ):
        """Test that decorated processor with PydanticQueue raises validation error."""
        queue: PydanticQueue[SimpleModel] = PydanticQueue(mock_queue, SimpleModel)

        @processor(queue)
        async def handle_model(data: SimpleModel) -> str:
            return f"{data.name}: {data.count}"

        with pytest.raises(ValidationError):
            await handle_model.process({"name": "test"})  # missing 'count'

    def test_processor_decorator_retry_on_option(self, mock_queue):
        """Test that processor decorator passes retry_on option."""

        @processor(mock_queue, retry_on=(ValueError, KeyError))
        async def handle_dict(data: dict) -> str:
            return f"{data['name']}: {data['count']}"

        assert handle_dict.retry_on == (ValueError, KeyError)

    def test_processor_decorator_retry_delay_option(self, mock_queue):
        """Test that processor decorator passes retry_delay option."""

        @processor(mock_queue, retry_delay=5.0)
        async def handle_dict(data: dict) -> str:
            return f"{data['name']}: {data['count']}"

        # retry_delay is converted to a callable internally
        assert callable(handle_dict.retry_delay)


class TestProcessorGrouped:
    """Tests for the grouped processor functionality."""

    def test_processor_default_grouped_is_false(self, mock_queue):
        """Test that grouped defaults to False."""

        @processor(mock_queue)
        async def handle_dict(data: dict) -> str:
            return f"{data['name']}: {data['count']}"

        assert handle_dict.grouped is False

    def test_processor_grouped_option(self, mock_queue):
        """Test that grouped option is passed to processor."""

        @processor(mock_queue, grouped=True)
        async def handle_dict(data: dict) -> str:
            return f"{data['name']}: {data['count']}"

        assert handle_dict.grouped is True

    def test_pydantic_processor_grouped_option(self, mock_queue):
        """Test that grouped option is passed to PydanticProcessor."""
        queue = PydanticQueue(mock_queue, SimpleModel)

        @processor(queue, grouped=True)
        async def handle_model(data: SimpleModel) -> str:
            return f"{data.name}: {data.count}"

        assert handle_model.grouped is True

    def test_processor_grouped_with_other_options(self, mock_queue):
        """Test that grouped option works with other processor options."""

        @processor(
            mock_queue,
            grouped=True,
            concurrency_limit=5,
            max_retries=2,
            timeout=30,
        )
        async def handle_dict(data: dict) -> str:
            return f"{data['name']}: {data['count']}"

        assert handle_dict.grouped is True
        assert handle_dict.concurrency_limit == 5
        assert handle_dict.max_retries == 2
        assert handle_dict.timeout == 30
