"""Order model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base, _utcnow


class OrderSide(str, PyEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, PyEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, PyEnum):
    INTENT = "intent"
    ACCEPTED = "accepted"
    RESTING = "resting"
    FILLING = "filling"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Order(Base):
    """Order record with full lifecycle tracking."""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    strategy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=True)

    # Venue fields
    venue_order_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    side: Mapped[str] = mapped_column(String(10), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="intent")

    # Price / size
    price: Mapped[float] = mapped_column(Float, nullable=True)
    stop_price: Mapped[float] = mapped_column(Float, nullable=True)
    size: Mapped[float] = mapped_column(Float, nullable=False)
    filled_size: Mapped[float] = mapped_column(Float, default=0.0)
    avg_fill_price: Mapped[float] = mapped_column(Float, nullable=True)

    leverage: Mapped[int] = mapped_column(Integer, default=1)
    reduce_only: Mapped[bool] = mapped_column(default=False)

    # Risk
    risk_pct: Mapped[float] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float] = mapped_column(Float, nullable=True)

    # Timing
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    filled_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Signal context
    signal_strength: Mapped[float] = mapped_column(Float, nullable=True)
    regime: Mapped[str] = mapped_column(String(20), nullable=True)
    rsi_1h: Mapped[float] = mapped_column(Float, nullable=True)
    rsi_4h: Mapped[float] = mapped_column(Float, nullable=True)
