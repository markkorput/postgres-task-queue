"""create-queue

Revision ID: 71d96b52b5ed
Revises:
Create Date: 2026-05-25 20:48:21.717306

"""

from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "71d96b52b5ed"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

QUEUE_NAME = "timers"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(f"select pgmq.create('{QUEUE_NAME}')")
    op.execute(f"select pgmq.create('{QUEUE_NAME}_dlq')")


def downgrade() -> None:
    """Downgrade scAlembic version, we may also attach an attributhema."""
    op.execute(f"select pgmq.drop_queue('{QUEUE_NAME}_dlq')")
    op.execute(f"select pgmq.drop_queue('{QUEUE_NAME}')")
