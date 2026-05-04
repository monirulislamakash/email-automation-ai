"""init

Revision ID: cca5e655cb4c
Revises: 
Create Date: 2025-11-13 14:05:46.997259
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON


# revision identifiers
revision: str = "cca5e655cb4c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """SQLite does NOT support ALTER COLUMN TYPE → recreate table"""

    # Create new table with JSON type
    op.create_table(
        "Campaigns_new",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_schedule", SQLITE_JSON(none_as_null=True)),
        sa.Column("options_settings", SQLITE_JSON(none_as_null=True)),
    )

    # Copy data
    op.execute("""
        INSERT INTO Campaigns_new (id, campaign_schedule, options_settings)
        SELECT id, campaign_schedule, options_settings
        FROM Campaigns
    """)

    # Drop old table
    op.drop_table("Campaigns")

    # Rename new → original
    op.rename_table("Campaigns_new", "Campaigns")


def downgrade() -> None:
    """Reverse: recreate old structure"""

    op.create_table(
        "Campaigns_old",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_schedule", sa.VARCHAR()),
        sa.Column("options_settings", sa.VARCHAR()),
    )

    op.execute("""
        INSERT INTO Campaigns_old (id, campaign_schedule, options_settings)
        SELECT id, campaign_schedule, options_settings
        FROM Campaigns
    """)

    op.drop_table("Campaigns")
    op.rename_table("Campaigns_old", "Campaigns")
