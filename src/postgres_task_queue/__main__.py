import datetime
import logging
import importlib
from typing import Annotated, Iterable
from collections.abc import Generator

from async_typer import AsyncTyper, Argument, Option

from .core.processor import Processor
from .core.worker import Worker

logger = logging.getLogger(__name__)


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
