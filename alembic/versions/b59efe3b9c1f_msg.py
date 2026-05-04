"""msg

Revision ID: b59efe3b9c1f
Revises: cca5e655cb4c
Create Date: 2025-11-16 13:32:50.590371
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "b59efe3b9c1f"
down_revision: Union[str, Sequence[str], None] = "cca5e655cb4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """SQLite SAFE type change: recreate column."""
    with op.batch_alter_table("Leads") as batch_op:
        batch_op.alter_column(
            "next_reply_date",
            existing_type=sa.DATE(),
            type_=sa.DateTime(),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Revert back to DATE."""
    with op.batch_alter_table("Leads") as batch_op:
        batch_op.alter_column(
            "next_reply_date",
            existing_type=sa.DateTime(),
            type_=sa.DATE(),
            existing_nullable=True,
        )
