"""Fill model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Float, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base
from app.models.order import OrderSide


class Fill(Base):
    """Execution fill record."""

    __tablename__ = "fills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    venue_fill_id: Mapped[str] = mapped_column(String(100), nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)

    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    size: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    fee_token: Mapped[str] = mapped_column(String(20), nullable=True)

    filled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
