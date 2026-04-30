"""Add symbol column to bot_states for multi-token support.

Revision ID: 0005_bot_state_symbol
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_bot_state_symbol"
down_revision = "0004_bot_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bot_states", sa.Column("symbol", sa.String(20), server_default="BTC", nullable=False))
    # Drop any existing unique constraint on user_id (name may vary)
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE bot_states DROP CONSTRAINT bot_states_user_id_key;
        EXCEPTION WHEN undefined_object THEN
            NULL;
        END $$;
    """)
    op.create_unique_constraint("uq_bot_states_user_symbol", "bot_states", ["user_id", "symbol"])


def downgrade() -> None:
    op.drop_constraint("uq_bot_states_user_symbol", "bot_states", type_="unique")
    op.drop_column("bot_states", "symbol")
