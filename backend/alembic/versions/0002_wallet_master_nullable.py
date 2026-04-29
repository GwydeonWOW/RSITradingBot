"""Make wallet master_address nullable

Revision ID: 0002_wallet_master_nullable
Revises: 0001_initial
Create Date: 2026-04-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_wallet_master_nullable"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "wallets",
        "master_address",
        existing_type=sa.String(255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "wallets",
        "master_address",
        existing_type=sa.String(255),
        nullable=False,
    )
