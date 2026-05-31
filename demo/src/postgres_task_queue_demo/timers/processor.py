import asyncio
import logging
from datetime import datetime

from postgres_task_queue.processor import processor

from ..db import get_db
from .models import Timer
from .queue import timers_queue, TimerInput

logger = logging.getLogger(__name__)


@processor(timers_queue, idempotency_key="key", lifo=True, grouped=True)
async def timers_processor(input: TimerInput) -> None:
    logger.info(f"Processing {repr(input.key)}: sleeping {input.delay} seconds...")
    started_at = datetime.now()
    await asyncio.sleep(input.delay)
    ended_at = datetime.now()

    with get_db() as session:
        timer = Timer(
            task_id=input.key,
            started_at=started_at,
            ended_at=ended_at,
        )
        session.add(timer)
        session.commit()
        logger.info(f"Created timer record for task {input.key} with id={timer.id}")

    logger.info("Done.")
