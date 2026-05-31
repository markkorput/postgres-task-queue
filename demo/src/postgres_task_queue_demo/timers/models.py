"""Timer model for the timers table."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Timer(Base):
    """Timer model representing a task timer record.

    Attributes:
        id: Primary key identifier.
        task_id: The ID of the task being timed.
        started_at: When the timer was started.
        ended_at: When the timer was ended.
    """

    __tablename__ = "timers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
