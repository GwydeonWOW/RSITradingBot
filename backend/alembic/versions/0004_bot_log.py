"""Create bot_logs table for decision tracking.

Revision ID: 0004_bot_log
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0004_bot_log"
down_revision = "0003_bot_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("level", sa.String(20), server_default="info"),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("symbol", sa.String(20), server_default="BTC"),
        sa.Column("regime", sa.String(20), nullable=True),
        sa.Column("rsi_4h", sa.Float, nullable=True),
        sa.Column("rsi_1h", sa.Float, nullable=True),
        sa.Column("price", sa.Float, nullable=True),
        sa.Column("signal_stage", sa.String(20), nullable=True),
        sa.Column("signal_type", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_bot_logs_created_at", "bot_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("bot_logs")
