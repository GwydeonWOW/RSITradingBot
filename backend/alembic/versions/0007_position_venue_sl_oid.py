"""Add venue_sl_oid column to positions table.

Stores the Hyperliquid order ID for the exchange-side stop-loss
trigger order so we can cancel it when closing the position.

Revision ID: 0007_position_venue_sl_oid
"""

from alembic import op

revision = "0007_position_venue_sl_oid"
down_revision = "0006_drop_user_id_unique_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("positions", op.Column("venue_sl_oid", op.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("positions", "venue_sl_oid")
