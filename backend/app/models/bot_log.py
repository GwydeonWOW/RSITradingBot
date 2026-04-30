"""Bot decision log — persists each cycle's decisions for the UI."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base, _utcnow


class BotLog(Base):
    __tablename__ = "bot_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    level: Mapped[str] = mapped_column(String(20), default="info")  # info, signal, trade, exit, error
    message: Mapped[str] = mapped_column(Text, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), default="BTC")

    regime: Mapped[str] = mapped_column(String(20), nullable=True)
    rsi_4h: Mapped[float] = mapped_column(Float, nullable=True)
    rsi_1h: Mapped[float] = mapped_column(Float, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=True)
    signal_stage: Mapped[str] = mapped_column(String(20), nullable=True)
    signal_type: Mapped[str] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
