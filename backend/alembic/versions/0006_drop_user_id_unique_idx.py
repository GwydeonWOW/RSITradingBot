"""Drop old unique index on bot_states.user_id.

Migration 0005 dropped the constraint but missed the unique INDEX
that SQLAlchemy's unique=True + index=True creates.

Revision ID: 0006_drop_user_id_unique_idx
"""

from alembic import op

revision = "0006_drop_user_id_unique_idx"
down_revision = "0005_bot_state_symbol"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            DROP INDEX IF EXISTS ix_bot_states_user_id;
        EXCEPTION WHEN undefined_object THEN
            NULL;
        END $$;
    """)


def downgrade() -> None:
    pass
