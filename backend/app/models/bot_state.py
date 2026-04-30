"""Bot state model — persists signal detector state between cycles."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base, _utcnow


class BotState(Base):
    __tablename__ = "bot_states"
    __table_args__ = (
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, default="BTC")

    regime: Mapped[str] = mapped_column(String(20), default="neutral")
    signal_stage: Mapped[str] = mapped_column(String(20), default="inactive")
    signal_type: Mapped[str] = mapped_column(String(20), default="none")
    rsi_at_setup: Mapped[float] = mapped_column(Float, default=0.0)
    bars_in_setup: Mapped[int] = mapped_column(Integer, default=0)
    rsi_extreme_in_zone: Mapped[float] = mapped_column(Float, default=0.0)

    last_regime: Mapped[str] = mapped_column(String(20), default="neutral")
    last_rsi_4h: Mapped[float] = mapped_column(Float, default=0.0)
    last_rsi_1h: Mapped[float] = mapped_column(Float, default=0.0)
    last_price: Mapped[float] = mapped_column(Float, default=0.0)
    last_signal_type: Mapped[str] = mapped_column(String(20), default="none")

    last_eval_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
