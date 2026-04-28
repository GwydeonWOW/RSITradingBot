"""Strategy model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.models.user import Base


class Strategy(Base):
    """Saved strategy configuration."""

    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="rsi")

    # RSI parameters stored as JSON for flexibility
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Universe and risk
    universe: Mapped[str] = mapped_column(String(500), nullable=False, default="BTC,ETH,SOL")
    max_leverage: Mapped[int] = mapped_column(Integer, default=3)
    risk_per_trade: Mapped[float] = mapped_column(Float, default=0.005)

    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
