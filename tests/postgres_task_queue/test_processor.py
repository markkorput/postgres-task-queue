from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel
from postgres_task_queue._broker import Broker, Task
from postgres_task_queue._processor import Processor, PydanticProcessor
from postgres_task_queue._queue import Queue, PydanticQueue


class SimpleModel(BaseModel):
    name: str
    count: int


class UserModel(BaseModel):
    username: str
    email: str
    age: int = 25


@pytest.fixture
def broker():
    mock = AsyncMock(spec=Broker)
    mock.queue_name = "test_queue"
    return mock


@pytest.fixture
def custom_broker():
    mock = AsyncMock(spec=Broker)
    mock.queue_name = "custom_queue"
    return mock


@pytest.fixture
def process_order_broker():
    mock = AsyncMock(spec=Broker)
    mock.queue_name = "process_order"
    return mock


class TestProcessorBasics:
    """Tests for basic Processor functionality."""

    def test_processor_requires_queue(self, broker):
        queue = Queue(broker)

        async def my_function(x: dict[str, Any]) -> int:
            return len(x)

        processor = Processor(my_function, queue)
        assert isinstance(processor, Processor)

    @pytest.mark.asyncio
    async def test_processor_fn_property(self, broker):
        queue = Queue(broker)

        async def original_fn(data: dict[str, Any]) -> int:
            return sum(data.values())

        processor = Processor(original_fn, queue)
        assert processor.fn is original_fn

    @pytest.mark.asyncio
    async def test_processor_call_executes_function(self, broker):
        queue = Queue(broker)

        async def add(data: dict[str, int]) -> int:
            return data["a"] + data["b"]

        processor = Processor(add, queue)
        assert await processor({"a": 2, "b": 3}) == 5
        assert await processor({"a": 10, "b": 20}) == 30

    @pytest.mark.asyncio
    async def test_processor_call_with_default_input(self, broker):
        queue = Queue(broker)

        async def greet(data: dict[str, str]) -> str:
            name = data.get("name", "World")
            greeting = data.get("greeting", "Hello")
            return f"{greeting}, {name}!"

        processor = Processor(greet, queue)
        assert await processor({"name": "World"}) == "Hello, World!"
        assert await processor({"name": "Alice", "greeting": "Hi"}) == "Hi, Alice!"

    def test_processor_stores_queue(self, custom_broker):
        queue = Queue(custom_broker)

        async def process_data(data: dict) -> None:
            pass

        processor = Processor(process_data, queue)
        assert processor.queue is queue
        assert processor.queue.broker.queue_name == "custom_queue"

    def test_function_name_as_queue_name(self, process_order_broker):
        queue = Queue(process_order_broker)

        async def process_order(data: dict) -> None:
            pass

        processor = Processor(process_order, queue)
        assert processor.queue.broker.queue_name == "process_order"


class TestProcessorMaxRetries:
    """Tests for Processor max_retries configuration."""

    def test_processor_with_max_retries(self, broker):
        queue = Queue(broker)

        async def my_processor_fn(data: dict) -> None:
            pass

        processor = Processor(my_processor_fn, queue, max_retries=5)
        assert processor.max_retries == 5

    def test_processor_default_max_retries(self, broker):
        queue = Queue(broker)

        async def my_processor_fn(data: dict) -> None:
            pass

        processor = Processor(my_processor_fn, queue)
        assert processor.max_retries == 0


class TestProcessorRetryOn:
    """Tests for Processor retry_on configuration."""

    def test_processor_with_retry_on_exceptions(self, broker):
        queue = Queue(broker)

        async def fetch_processor_fn(data: dict) -> None:
            pass

        processor = Processor(
            fetch_processor_fn,
            queue,
            max_retries=3,
            retry_on=(ConnectionError, TimeoutError),
        )
        assert processor.retry_on == (ConnectionError, TimeoutError)

    def test_processor_with_retry_on_callable(self, broker):
        queue = Queue(broker)

        def predicate(e: Exception) -> bool:
            return isinstance(e, ValueError)

        async def validate_processor_fn(data: dict) -> None:
            pass

        processor = Processor(
            validate_processor_fn, queue, max_retries=3, retry_on=predicate
        )
        assert processor.retry_on is predicate

    def test_processor_default_retry_on_none(self, broker):
        queue = Queue(broker)

        async def default_processor_fn(data: dict) -> None:
            pass

        processor = Processor(default_processor_fn, queue, max_retries=3)
        assert processor.retry_on is None

    def test_processor_retry_on_with_generator(self, broker):
        queue = Queue(broker)

        async def file_processor_fn(data: dict) -> None:
            pass

        processor = Processor(
            file_processor_fn, queue, max_retries=3, retry_on=(OSError,)
        )
        assert processor.retry_on == (OSError,)


class TestProcessorRetryDelay:
    """Tests for Processor retry_delay configuration."""

    def test_processor_with_retry_delay_fixed(self, broker):
        queue = Queue(broker)

        async def fetch_processor_fn(data: dict) -> None:
            pass

        processor = Processor(fetch_processor_fn, queue, max_retries=3, retry_delay=5.0)
        assert callable(processor.retry_delay)
        assert processor.retry_delay(1) == 5.0
        assert processor.retry_delay(2) == 5.0

    def test_processor_with_retry_delay_callable(self, broker):
        queue = Queue(broker)

        def delay_func(n: int) -> float:
            return n * 2.0

        async def scalable_processor_fn(data: dict) -> None:
            pass

        processor = Processor(
            scalable_processor_fn, queue, max_retries=3, retry_delay=delay_func
        )
        assert callable(processor.retry_delay)
        assert processor.retry_delay(1) == 2.0
        assert processor.retry_delay(2) == 4.0

    def test_processor_default_retry_delay_none(self, broker):
        queue = Queue(broker)

        async def default_processor_fn(data: dict) -> None:
            pass

        processor = Processor(default_processor_fn, queue, max_retries=3)
        assert callable(processor.retry_delay)
        assert processor.retry_delay(1) == 0.0
        assert processor.retry_delay(2) == 0.0

    def test_processor_retry_delay_with_prebuilt_fixed(self, broker):
        from postgres_task_queue.retry import fixed

        queue = Queue(broker)

        async def processor_fn(data: dict) -> None:
            pass

        processor = Processor(
            processor_fn, queue, max_retries=3, retry_delay=fixed(10.0)
        )
        assert callable(processor.retry_delay)
        assert processor.retry_delay(1) == 10.0
        assert processor.retry_delay(2) == 10.0

    def test_processor_retry_delay_with_prebuilt_linear(self, broker):
        from postgres_task_queue.retry import linear

        queue = Queue(broker)

        async def processor_fn(data: dict) -> None:
            pass

        processor = Processor(
            processor_fn, queue, max_retries=3, retry_delay=linear(5.0)
        )
        assert callable(processor.retry_delay)
        assert processor.retry_delay(1) == 5.0
        assert processor.retry_delay(2) == 10.0
        assert processor.retry_delay(3) == 15.0

    def test_processor_retry_delay_with_prebuilt_exponential(self, broker):
        from postgres_task_queue.retry import exponential

        queue = Queue(broker)

        async def processor_fn(data: dict) -> None:
            pass

        processor = Processor(
            processor_fn, queue, max_retries=3, retry_delay=exponential(max_delay=60.0)
        )
        assert callable(processor.retry_delay)
        assert processor.retry_delay(1) == 2.0  # 2^1
        assert processor.retry_delay(2) == 4.0  # 2^2
        assert processor.retry_delay(3) == 8.0  # 2^3

    def test_processor_retry_delay_with_prebuilt_exponential_capped(self, broker):
        from postgres_task_queue.retry import exponential

        queue = Queue(broker)

        async def processor_fn(data: dict) -> None:
            pass

        processor = Processor(
            processor_fn, queue, max_retries=5, retry_delay=exponential(max_delay=5.0)
        )
        assert callable(processor.retry_delay)
        assert processor.retry_delay(1) == 2.0
        assert processor.retry_delay(2) == 4.0
        assert processor.retry_delay(3) == 5.0  # capped at 5.0
        assert processor.retry_delay(4) == 5.0  # capped at 5.0

    def test_processor_with_both_retry_on_and_retry_delay(self, broker):
        from postgres_task_queue.retry import exponential

        queue = Queue(broker)

        async def resilient_processor_fn(data: dict) -> None:
            pass

        processor = Processor(
            resilient_processor_fn,
            queue,
            max_retries=3,
            retry_on=(ConnectionError, TimeoutError),
            retry_delay=exponential(max_delay=60),
        )
        assert processor.retry_on == (ConnectionError, TimeoutError)
        assert callable(processor.retry_delay)


@pytest.mark.asyncio
class TestProcessorProcess:
    """Tests for Processor.process() method."""

    async def test_process_without_input_model(self, broker):
        queue = Queue(broker)

        async def simple_function(data: dict[str, int]) -> int:
            return data["value"]

        processor = Processor(simple_function, queue)
        result = await processor.process({"value": 42})
        assert result == 42


@pytest.mark.asyncio
class TestIdempotencyKey:
    """Tests for Processor idempotency_key option."""

    async def test_adds_msg_id_to_payload(self, broker):
        """Test that Processor adds msg_id to payload when idempotency_key is set."""
        capture = AsyncMock()
        queue = Queue(broker)

        processor = Processor(capture, queue, idempotency_key="msg_id")

        task = Task(id=123, payload={"name": "test"})
        await processor.process_task(task)

        capture.assert_called_once_with({**task.payload, "msg_id": str(task.id)})

    async def test_works_with_pydantic_processor_if_model_has_the_given_attribute(
        self, broker
    ):
        """Test that PydanticProcessor adds msg_id to payload when idempotency_key is set."""

        class FlexibleModel(BaseModel):
            name: str
            count: int
            task_id: str

        capture = AsyncMock()
        queue = PydanticQueue[FlexibleModel](broker, FlexibleModel)

        processor = PydanticProcessor(capture, queue, idempotency_key="task_id")

        task = Task(id=456, payload={"name": "hello", "count": 10})
        await processor.process_task(task)

        capture.assert_called_once_with(
            FlexibleModel(
                name=task.payload["name"],
                count=task.payload["count"],
                task_id=str(task.id),
            )
        )


class TestProcessorShouldRetryException:
    """Tests for Processor._should_retry_exception method."""

    @pytest.fixture
    def task_with_retry_on_tuple(self, broker):
        """Processor configured to retry only on specific exceptions."""
        queue = Queue(broker)

        async def dummy_task(data: dict) -> None:
            pass

        return Processor(
            dummy_task, queue, max_retries=3, retry_on=(ConnectionError, TimeoutError)
        )

    @pytest.fixture
    def task_with_retry_on_callable(self, broker):
        """Processor configured with a callable retry predicate."""
        queue = Queue(broker)

        async def dummy_task(data: dict) -> None:
            pass

        return Processor(
            dummy_task,
            queue,
            max_retries=3,
            retry_on=lambda e: isinstance(e, ValueError) and e.args[0] == "retry",
        )

    @pytest.fixture
    def task_with_retry_on_none(self, broker):
        """Processor configured with default retry_on (None)."""
        queue = Queue(broker)

        async def dummy_task(data: dict) -> None:
            pass

        return Processor(dummy_task, queue, max_retries=3)

    @pytest.fixture
    def dummy_task(self):
        """Dummy task for Processor tests."""
        return Task(id=1, payload={})

    def test_retry_on_none_retries_all(self, task_with_retry_on_none, dummy_task):
        """When retry_on is None, all exceptions should be retried."""
        assert (
            task_with_retry_on_none._should_retry_exception(ValueError("test")) is True
        )
        assert (
            task_with_retry_on_none._should_retry_exception(TypeError("test")) is True
        )
        assert (
            task_with_retry_on_none._should_retry_exception(RuntimeError("test"))
            is True
        )

    def test_retry_on_tuple_matches_specific_exceptions(
        self, task_with_retry_on_tuple, dummy_task
    ):
        """When retry_on is a tuple, only matching exception types should be retried."""
        assert (
            task_with_retry_on_tuple._should_retry_exception(ConnectionError("test"))
            is True
        )
        assert (
            task_with_retry_on_tuple._should_retry_exception(TimeoutError("test"))
            is True
        )
        assert (
            task_with_retry_on_tuple._should_retry_exception(ValueError("test"))
            is False
        )
        assert (
            task_with_retry_on_tuple._should_retry_exception(TypeError("test")) is False
        )

    def test_retry_on_tuple_matches_subclasses(
        self, task_with_retry_on_tuple, dummy_task
    ):
        """When retry_on is a tuple, it should match subclasses of specified exceptions."""
        # ConnectionRefusedError is a subclass of ConnectionError
        assert (
            task_with_retry_on_tuple._should_retry_exception(
                ConnectionRefusedError("refused")
            )
            is True
        )

    def test_retry_on_callable_uses_predicate(
        self, task_with_retry_on_callable, dummy_task
    ):
        """When retry_on is a callable, it should use the predicate to determine if retry."""
        assert (
            task_with_retry_on_callable._should_retry_exception(ValueError("retry"))
            is True
        )
        assert (
            task_with_retry_on_callable._should_retry_exception(ValueError("no retry"))
            is False
        )
        assert (
            task_with_retry_on_callable._should_retry_exception(TypeError("test"))
            is False
        )

    def test_retry_on_empty_tuple_retries_nothing(self, dummy_task, broker):
        """When retry_on is an empty tuple, no exceptions should be retried."""
        queue = Queue(broker)

        async def my_dummy_task(data: dict) -> None:
            pass

        processor = Processor(my_dummy_task, queue, max_retries=3, retry_on=())
        assert processor._should_retry_exception(ValueError("test")) is False
        assert processor._should_retry_exception(ConnectionError("test")) is False

    def test_retry_on_with_multiple_exception_types(self, dummy_task, broker):
        """Test retry_on with multiple exception types in tuple."""
        queue = Queue(broker)

        async def my_dummy_task(data: dict) -> None:
            pass

        processor = Processor(
            my_dummy_task,
            queue,
            max_retries=3,
            retry_on=(ConnectionError, TimeoutError, OSError),
        )
        assert processor._should_retry_exception(ConnectionError("test")) is True
        assert processor._should_retry_exception(TimeoutError("test")) is True
        assert processor._should_retry_exception(OSError("test")) is True
        assert (
            processor._should_retry_exception(FileNotFoundError("test")) is True
        )  # subclass of OSError
        assert processor._should_retry_exception(ValueError("test")) is False


class TestPydanticProcessor:
    """Tests for Processor with pydantic input models."""

    @pytest.fixture
    def processor(self, broker) -> PydanticProcessor[SimpleModel]:
        queue = PydanticQueue[SimpleModel](broker, SimpleModel)

        async def process_model_fn(data: SimpleModel) -> str:
            return f"{data.name}: {data.count}"

        processor = PydanticProcessor(process_model_fn, queue)
        return processor

    @pytest.mark.asyncio
    async def test_processor_with_input_model(
        self, processor: PydanticProcessor[SimpleModel]
    ):
        assert processor.input_model is SimpleModel
        result = await processor(SimpleModel(name="test", count=5))
        assert result == "test: 5"

    @pytest.mark.asyncio
    async def test_process_with_input_model_validates_dict(
        self, processor: PydanticProcessor[SimpleModel]
    ):
        result = await processor.process({"name": "test", "count": 5})
        assert result == "test: 5"

    @pytest.mark.asyncio
    async def test_process_with_input_model_raises_validation_error(
        self, processor: PydanticProcessor[SimpleModel]
    ):
        with pytest.raises(Exception):  # ValidationError from pydantic
            await processor.process({"name": "test"})  # missing 'count'
