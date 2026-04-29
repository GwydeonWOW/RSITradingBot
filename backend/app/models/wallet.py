"""Wallet model for Hyperliquid agent wallets."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base, _utcnow


class Wallet(Base):
    """Hyperliquid agent wallet (non-custodial model).

    The user's master wallet approves an agent wallet.
    The agent's encrypted private key is stored here for signing transactions.
    """

    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    label: Mapped[str] = mapped_column(String(100), nullable=False, default="main")
    master_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    agent_address: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_private_key: Mapped[str] = mapped_column(String(1024), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    nonce_tracker: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
