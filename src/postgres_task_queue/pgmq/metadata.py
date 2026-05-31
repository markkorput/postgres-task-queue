"""Metadata enums for pgtq message headers and status."""

from enum import StrEnum, auto


class Header(StrEnum):
    """Custom pgtq message headers."""

    STATUS = auto()
    DLQ = auto()
    ERRORS = auto()
    ORIGINAL = auto()
    RETRY = auto()

    def full_name(self) -> str:
        """Return the full header name with x-pgtq- prefix."""
        return f"x-pgtq-{self.value}"


class MessageStatus(StrEnum):
    """Message processing status values."""

    QUEUED = auto()
    PROCESSING = auto()
    FAILED = auto()
    COMPLETED = auto()
