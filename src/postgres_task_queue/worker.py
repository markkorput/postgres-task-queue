import asyncio
import datetime
import logging
import importlib
from typing import Annotated, Iterable
from collections.abc import Generator

from async_typer import AsyncTyper, Argument, Option

from ._broker import Task
from ._processor import Processor

logger = logging.getLogger(__name__)


class ProcessorWorker:
    def __init__(
        self,
        processor: Processor,
        *,
        poll_interval_ms: int = 1000,
        max_poll_seconds: int = 60,
        prune_interval: datetime.timedelta | None = datetime.timedelta(minutes=60),
        prune_batch_size: int = 1000,
    ) -> None:
        self.processor = processor
        self.poll_interval_ms = poll_interval_ms
        self.max_poll_seconds = max_poll_seconds
        self.prune_interval = prune_interval
        self.prune_batch_size = prune_batch_size
        self._next_prune_at = self._next_prune()

    async def poll(self, batch_size: int) -> tuple[Task, ...]:
        """Poll for tasks from the processor's queue."""
        return await self.processor.poll(
            batch_size,
            max_poll_seconds=self.max_poll_seconds,
            poll_interval_ms=self.poll_interval_ms,
        )

    def _next_prune(self) -> datetime.datetime | None:
        return (
            (datetime.datetime.now(datetime.timezone.utc) + self.prune_interval)
            if self.prune_interval
            else None
        )

    def should_prune(self) -> bool:
        """Check if pruning should be performed based on the prune_interval."""
        return self._next_prune_at is not None and (
            self._next_prune_at <= datetime.datetime.now(datetime.timezone.utc)
        )

    async def prune(self) -> None:
        """Perform pruning and update the last pruned timestamp."""
        await self.processor.queue.prune(batch_size=self.prune_batch_size)
        self._next_prune_at = self._next_prune()


class Worker:
    def __init__(
        self,
        processors: Iterable[Processor],
        concurrency_limit: int = 1,
        poll_interval_seconds: float = 1.0,
        poll_exception_interval_seconds: float = 5.0,
        prune_interval: datetime.timedelta | None = datetime.timedelta(hours=12),
        prune_batch_size: int = 1000,
    ):
        self.processors = set(processors)
        self.concurrency_limit = concurrency_limit
        self.poll_interval_seconds = poll_interval_seconds
        self.poll_exception_interval_seconds = poll_exception_interval_seconds
        self.prune_interval = prune_interval
        self.prune_batch_size = prune_batch_size

        # Start will all "slots" available
        self.free_slots = concurrency_limit

    async def run(self) -> None:
        """Start independent poll loops for each processor."""

        await asyncio.gather(
            *[
                self._loop(
                    ProcessorWorker(
                        processor,
                        prune_interval=self.prune_interval,
                        prune_batch_size=self.prune_batch_size,
                    )
                )
                for processor in self.processors
            ]
        )

    async def _loop(self, processor_worker: ProcessorWorker):
        # This processor worker loop runs indefinitely
        while True:
            # Any exception is caught, logged and silenced to keep this processor worker loop alive
            try:
                # Check available worker-level concurrency slots to avoid unnecessary polling
                if self.free_slots:
                    # Poll for messages (only poll for max. the number of messages we can process right now)
                    if tasks := await processor_worker.poll(self.free_slots):
                        for task in tasks:
                            # start a process processor for each message, don't await the processing; this allows
                            # parallel (concurrent) processing when enabled (the Processor.process_task method will
                            # check and respect the processor-level concurrency settings
                            asyncio.create_task(
                                self._process(
                                    task,
                                    processor_worker.processor,
                                )
                            )
                    else:
                        # Check if we should prune when no messages were polled
                        if processor_worker.should_prune():
                            await processor_worker.prune()

                # Short sleep to avoid hammering the DB with poll requests (messages are processed
                # in asynchronous tasks, so this while loop would otherwise execute non-stop)
                await asyncio.sleep(self.poll_interval_seconds)
            except Exception as e:
                logger.exception(
                    f"Error polling queue '{processor_worker.processor.queue.broker.queue_name}': {e}"
                )
                # This sleep is generally a bit longer than the regular interval sleep,
                # to reduce polling frequency when there are DB/connection issues
                await asyncio.sleep(self.poll_exception_interval_seconds)

    async def _process(self, task: Task, processor: Processor) -> None:
        # Respect worker-level concurrency-limit
        if not self._claim_slot():
            return

        try:
            # Start processing (processor-level concurrency check happens in Processor.process_task)
            await processor.process_task(task)
        finally:
            # Free the processing slot that was claimed at the start of this function
            self._free_slot()

    def _claim_slot(self) -> bool:
        if self.free_slots < 1:
            return False
        self.free_slots -= 1
        logger.debug(
            f"Claimed slot ({self.free_slots}/{self.concurrency_limit} slots free)"
        )
        return True

    def _free_slot(self) -> None:
        self.free_slots += 1
        logger.debug(
            f"Freed slot ({self.free_slots}/{self.concurrency_limit} slots free)"
        )


def _get_processors(module_path: str) -> Generator[Processor, None, None]:
    module = importlib.import_module(module_path)
    yield from (obj for _, obj in vars(module).items() if isinstance(obj, Processor))


def _collect_processors(
    modules: Iterable[str],
    *,
    include: set[str],
    exclude: set[str],
) -> Generator[Processor, None, None]:
    for module_path in set(modules):
        for processor in _get_processors(module_path):
            if include and processor.queue.broker.queue_name not in include:
                continue
            if exclude and processor.queue.broker.queue_name in exclude:
                continue

            yield processor


app = AsyncTyper()


@app.command()
async def worker(
    modules: Annotated[
        list[str],
        Argument(help="Python module import paths to scan for Processor instances"),
    ],
    include: Annotated[
        list[str] | None,
        Option(
            help="Explicit whitelist of processors, by their queue_name, to include"
        ),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        Option(
            help="Explicit blacklist of processors, by their queue_name, to exclude"
        ),
    ] = None,
    concurrency_limit: Annotated[
        int,
        Option(help="Number of concurrent processors this worker can execute"),
    ] = 1,
    poll_interval_seconds: Annotated[
        float,
        Option(help="Interval in seconds between poll attempts"),
    ] = 1.0,
    poll_exception_interval_seconds: Annotated[
        float,
        Option(
            help="Interval in seconds between poll attempts when an exception occurs"
        ),
    ] = 5.0,
    prune_interval: Annotated[
        int | None,
        Option(help="Pruning interval in minutes (None disables pruning)"),
    ] = 60,
    prune_batch_size: Annotated[
        int,
        Option(help="Maximum number of archived messages to prune in one batch"),
    ] = 1000,
):
    """Worker command that scans modules for Processor instances and starts a worker process for those processors."""

    from postgres_task_queue.pgmq.container import Container, wire

    container = Container()
    wire(container)

    processors = set(
        _collect_processors(
            modules, include=set(include or []), exclude=set(exclude or [])
        )
    )

    logger.info(
        f"Starting worker for processors: {', '.join(sorted(p.queue.broker.queue_name for p in processors))}"
    )

    # Convert prune_interval from minutes (int) to timedelta
    prune_interval_td: datetime.timedelta | None = (
        datetime.timedelta(minutes=prune_interval)
        if prune_interval is not None
        else None
    )

    await Worker(
        processors,
        concurrency_limit=concurrency_limit,
        poll_interval_seconds=poll_interval_seconds,
        poll_exception_interval_seconds=poll_exception_interval_seconds,
        prune_interval=prune_interval_td,
        prune_batch_size=prune_batch_size,
    ).run()


if __name__ == "__main__":
    app()
