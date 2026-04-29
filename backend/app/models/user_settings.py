"""Per-user strategy and risk settings."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base, _utcnow


class UserSettings(Base):
    """User-specific strategy, risk, and API configuration.

    Each user has one settings row. Null values mean "use system default".
    """

    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)

    # RSI Strategy
    rsi_period: Mapped[int] = mapped_column(Integer, default=14)
    rsi_regime_bullish_threshold: Mapped[float] = mapped_column(Float, default=55.0)
    rsi_regime_bearish_threshold: Mapped[float] = mapped_column(Float, default=45.0)
    rsi_signal_long_pullback_low: Mapped[float] = mapped_column(Float, default=40.0)
    rsi_signal_long_pullback_high: Mapped[float] = mapped_column(Float, default=48.0)
    rsi_signal_long_reclaim: Mapped[float] = mapped_column(Float, default=50.0)
    rsi_signal_short_bounce_low: Mapped[float] = mapped_column(Float, default=52.0)
    rsi_signal_short_bounce_high: Mapped[float] = mapped_column(Float, default=60.0)
    rsi_signal_short_lose: Mapped[float] = mapped_column(Float, default=50.0)
    rsi_exit_partial_r: Mapped[float] = mapped_column(Float, default=1.5)
    rsi_exit_breakeven_r: Mapped[float] = mapped_column(Float, default=1.0)
    rsi_exit_max_hours: Mapped[int] = mapped_column(Integer, default=36)

    # Risk
    risk_per_trade_min: Mapped[float] = mapped_column(Float, default=0.0025)
    risk_per_trade_max: Mapped[float] = mapped_column(Float, default=0.0075)
    max_leverage: Mapped[int] = mapped_column(Integer, default=3)
    max_total_exposure_pct: Mapped[float] = mapped_column(Float, default=0.30)

    # Universe (comma-separated symbols)
    universe: Mapped[str] = mapped_column(String(500), default="BTC,ETH,SOL")

    # Third-party API keys (per-user)
    zai_api_key: Mapped[str] = mapped_column(String(255), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
