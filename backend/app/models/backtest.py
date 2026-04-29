"""Backtest model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base, _utcnow


class Backtest(Base):
    """Backtest run record."""

    __tablename__ = "backtests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    strategy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    # Parameters snapshot
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    universe: Mapped[str] = mapped_column(String(500), nullable=False)

    # Date range
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Results
    metrics: Mapped[dict] = mapped_column(JSON, nullable=True)
    equity_curve: Mapped[dict] = mapped_column(JSON, nullable=True)
    trades_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
