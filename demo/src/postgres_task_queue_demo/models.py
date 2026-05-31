"""This module collects all DB models"""

from .db import Base
from .timers.models import Timer

__all__ = ["Base", "Timer"]
