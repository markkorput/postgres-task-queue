from pydantic import BaseModel
from postgres_task_queue import create_queue


class TimerInput(BaseModel):
    delay: float
    key: str


timers_queue = create_queue(
    "timers",
    input_model=TimerInput,
)
