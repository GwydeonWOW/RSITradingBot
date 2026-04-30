"""Create bot_states table for persisting signal detector state.

Revision ID: 0003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_states",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), unique=True, nullable=False, index=True),
        sa.Column("regime", sa.String(20), server_default="neutral"),
        sa.Column("signal_stage", sa.String(20), server_default="inactive"),
        sa.Column("signal_type", sa.String(20), server_default="none"),
        sa.Column("rsi_at_setup", sa.Float, server_default="0"),
        sa.Column("bars_in_setup", sa.Integer, server_default="0"),
        sa.Column("rsi_extreme_in_zone", sa.Float, server_default="0"),
        sa.Column("last_regime", sa.String(20), server_default="neutral"),
        sa.Column("last_rsi_4h", sa.Float, server_default="0"),
        sa.Column("last_rsi_1h", sa.Float, server_default="0"),
        sa.Column("last_price", sa.Float, server_default="0"),
        sa.Column("last_signal_type", sa.String(20), server_default="none"),
        sa.Column("last_eval_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("bot_states")
