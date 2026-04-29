"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("label", sa.String(100), nullable=False, server_default="main"),
        sa.Column("master_address", sa.String(255), nullable=False),
        sa.Column("agent_address", sa.String(255), nullable=False),
        sa.Column("encrypted_private_key", sa.String(1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("nonce_tracker", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("hashed_key", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, server_default="default"),
        sa.Column("permissions", sa.String(200), nullable=False, server_default="read"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="rsi"),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("universe", sa.String(500), nullable=False, server_default="BTC,ETH,SOL"),
        sa.Column("max_leverage", sa.Integer(), server_default=sa.text("3"), nullable=True),
        sa.Column("risk_per_trade", sa.Float(), server_default=sa.text("0.005"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=True),
        sa.Column("venue_order_id", sa.String(100), nullable=True, index=True),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="intent"),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("stop_price", sa.Float(), nullable=True),
        sa.Column("size", sa.Float(), nullable=False),
        sa.Column("filled_size", sa.Float(), server_default=sa.text("0"), nullable=True),
        sa.Column("avg_fill_price", sa.Float(), nullable=True),
        sa.Column("leverage", sa.Integer(), server_default=sa.text("1"), nullable=True),
        sa.Column("reduce_only", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("risk_pct", sa.Float(), nullable=True),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("take_profit", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("filled_at", sa.DateTime(), nullable=True),
        sa.Column("signal_strength", sa.Float(), nullable=True),
        sa.Column("regime", sa.String(20), nullable=True),
        sa.Column("rsi_1h", sa.Float(), nullable=True),
        sa.Column("rsi_4h", sa.Float(), nullable=True),
    )

    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("size", sa.Float(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("leverage", sa.Integer(), server_default=sa.text("1"), nullable=True),
        sa.Column("unrealized_pnl", sa.Float(), server_default=sa.text("0"), nullable=True),
        sa.Column("realized_pnl", sa.Float(), server_default=sa.text("0"), nullable=True),
        sa.Column("partial_exited", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("be_moved", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "fills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("venue_fill_id", sa.String(100), nullable=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("size", sa.Float(), nullable=False),
        sa.Column("fee", sa.Float(), server_default=sa.text("0"), nullable=True),
        sa.Column("fee_token", sa.String(20), nullable=True),
        sa.Column("filled_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("positions.id"), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("balance_after", sa.Float(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "backtests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=True),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("universe", sa.String(500), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("equity_curve", sa.JSON(), nullable=True),
        sa.Column("trades_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "user_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), unique=True, nullable=False, index=True),
        sa.Column("rsi_period", sa.Integer(), server_default=sa.text("14"), nullable=True),
        sa.Column("rsi_regime_bullish_threshold", sa.Float(), server_default=sa.text("55"), nullable=True),
        sa.Column("rsi_regime_bearish_threshold", sa.Float(), server_default=sa.text("45"), nullable=True),
        sa.Column("rsi_signal_long_pullback_low", sa.Float(), server_default=sa.text("40"), nullable=True),
        sa.Column("rsi_signal_long_pullback_high", sa.Float(), server_default=sa.text("48"), nullable=True),
        sa.Column("rsi_signal_long_reclaim", sa.Float(), server_default=sa.text("50"), nullable=True),
        sa.Column("rsi_signal_short_bounce_low", sa.Float(), server_default=sa.text("52"), nullable=True),
        sa.Column("rsi_signal_short_bounce_high", sa.Float(), server_default=sa.text("60"), nullable=True),
        sa.Column("rsi_signal_short_lose", sa.Float(), server_default=sa.text("50"), nullable=True),
        sa.Column("rsi_exit_partial_r", sa.Float(), server_default=sa.text("1.5"), nullable=True),
        sa.Column("rsi_exit_breakeven_r", sa.Float(), server_default=sa.text("1"), nullable=True),
        sa.Column("rsi_exit_max_hours", sa.Integer(), server_default=sa.text("36"), nullable=True),
        sa.Column("risk_per_trade_min", sa.Float(), server_default=sa.text("0.0025"), nullable=True),
        sa.Column("risk_per_trade_max", sa.Float(), server_default=sa.text("0.0075"), nullable=True),
        sa.Column("max_leverage", sa.Integer(), server_default=sa.text("3"), nullable=True),
        sa.Column("max_total_exposure_pct", sa.Float(), server_default=sa.text("0.30"), nullable=True),
        sa.Column("universe", sa.String(500), server_default="BTC,ETH,SOL", nullable=True),
        sa.Column("zai_api_key", sa.String(255), server_default="", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("user_settings")
    op.drop_table("backtests")
    op.drop_table("ledger_entries")
    op.drop_table("fills")
    op.drop_table("positions")
    op.drop_table("orders")
    op.drop_table("strategies")
    op.drop_table("api_keys")
    op.drop_table("wallets")
    op.drop_table("users")
