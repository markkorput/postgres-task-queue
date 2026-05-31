from fastapi import FastAPI
from postgres_task_queue.pgmq.fastapi import create_router
from .timers.queue import timers_queue

app = FastAPI(
    title="Postgres Task Queue Demo",
)

app.include_router(create_router(timers_queue), prefix="/queues")
