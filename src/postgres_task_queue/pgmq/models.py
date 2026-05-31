"""Pydantic models for pgtq messages."""

from pydantic import BaseModel


class DlqBody(BaseModel):
    """Model for a DLQ message's body."""

    msg_id: int
    queue_name: str
    message: dict
    errors: list[str]
