from typing import Annotated
import random
import logging

import async_typer
from postgres_task_queue import setup


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

typer = async_typer.AsyncTyper()


@typer.async_command()
async def schedule(delay: float | None = None) -> None:
    if delay is None:
        delay = random.random()

    from .timers import queue

    logger.info(f"Creating timers queue item with {delay=}")
    await queue.timers_queue.enqueue(
        queue.TimerInput(
            delay=delay,
            key="",
        )
    )


@typer.async_command()
async def reschedule(dlq_id: int) -> None:
    from .timers import queue

    logger.info(f"Rescheduling timer DLQ #{dlq_id}")
    await queue.timers_queue.reschedule(dlq_id)


@typer.async_command()
async def worker():
    from postgres_task_queue.worker import Worker
    from .timers.processor import timers_processor

    worker = Worker({timers_processor})

    logger.info("Starting worker...")
    await worker.run()


@typer.async_command()
async def api(
    host: Annotated[str, async_typer.Option(help="Host to bind to")] = "0.0.0.0",
    port: Annotated[int, async_typer.Option(help="Port to listen on")] = 8000,
) -> None:
    """Run FastAPI server."""

    import uvicorn
    from .api import app

    config = uvicorn.Config(app, host=host, port=port)
    server = uvicorn.Server(config)

    await server.serve()


if __name__ == "__main__":
    from .db import async_db

    setup(connection=async_db)

    typer()
