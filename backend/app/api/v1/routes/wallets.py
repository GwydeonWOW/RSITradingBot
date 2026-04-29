"""Wallet management routes: connect, list, deactivate, balance."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user
from app.core.crypto import encrypt_private_key
from app.dependencies import get_db
from app.models.user import User
from app.models.wallet import Wallet

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectWalletRequest(BaseModel):
    label: str
    agent_address: str
    private_key: str
    master_address: Optional[str] = None


class WalletResponse(BaseModel):
    id: str
    label: str
    master_address: Optional[str]
    agent_address: str
    is_active: bool


class BalanceResponse(BaseModel):
    account_value: float
    total_raw_usd: float
    margin_used: float
    withdrawable: float
    unrealized_pnl: float


class UpdateWalletRequest(BaseModel):
    master_address: Optional[str] = None


def _query_address(wallet: Wallet) -> str:
    """Return the best address for Hyperliquid queries.

    Per Hyperliquid docs, queries should use the master account address.
    Agent address queries return empty results.
    """
    return wallet.master_address or wallet.agent_address


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def connect_wallet(
    request: ConnectWalletRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    """Connect an agent wallet. The private key is encrypted before storage."""
    encrypted = encrypt_private_key(request.private_key, settings.encryption_key)

    wallet = Wallet(
        user_id=current_user.id,
        label=request.label,
        master_address=request.master_address,
        agent_address=request.agent_address,
        encrypted_private_key=encrypted,
    )
    db.add(wallet)
    await db.flush()

    return WalletResponse(
        id=str(wallet.id),
        label=wallet.label,
        master_address=wallet.master_address,
        agent_address=wallet.agent_address,
        is_active=wallet.is_active,
    )


@router.get("", response_model=list[WalletResponse])
async def list_wallets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WalletResponse]:
    """List the current user's wallets. Never returns private keys."""
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id, Wallet.is_active.is_(True))
    )
    wallets = result.scalars().all()
    return [
        WalletResponse(
            id=str(w.id),
            label=w.label,
            master_address=w.master_address,
            agent_address=w.agent_address,
            is_active=w.is_active,
        )
        for w in wallets
    ]


@router.patch("/{wallet_id}", response_model=WalletResponse)
async def update_wallet(
    wallet_id: str,
    request: UpdateWalletRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WalletResponse:
    """Update wallet fields (e.g. add master address for balance queries)."""
    try:
        uuid.UUID(wallet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid wallet ID format")

    result = await db.execute(
        select(Wallet).where(
            Wallet.id == wallet_id,
            Wallet.user_id == current_user.id,
            Wallet.is_active.is_(True),
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if request.master_address is not None:
        wallet.master_address = request.master_address
    await db.flush()

    return WalletResponse(
        id=str(wallet.id),
        label=wallet.label,
        master_address=wallet.master_address,
        agent_address=wallet.agent_address,
        is_active=wallet.is_active,
    )


@router.delete("/{wallet_id}")
async def deactivate_wallet(
    wallet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a wallet (soft delete)."""
    try:
        uuid.UUID(wallet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid wallet ID format")

    result = await db.execute(
        select(Wallet).where(
            Wallet.id == wallet_id,
            Wallet.user_id == current_user.id,
            Wallet.is_active.is_(True),
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")
    wallet.is_active = False
    await db.flush()
    return {"status": "deactivated", "wallet_id": wallet_id}


@router.get("/{wallet_id}/balance", response_model=BalanceResponse)
async def get_wallet_balance(
    wallet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BalanceResponse:
    """Fetch wallet balance from Hyperliquid.

    Uses the master address for queries (agent address returns empty per docs).
    """
    try:
        uuid.UUID(wallet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid wallet ID format")

    result = await db.execute(
        select(Wallet).where(
            Wallet.id == wallet_id,
            Wallet.user_id == current_user.id,
            Wallet.is_active.is_(True),
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    query_address = _query_address(wallet)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "clearinghouseState", "user": query_address},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("Hyperliquid balance lookup failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to fetch balance from Hyperliquid")

    margin_summary = data.get("marginSummary", {})
    account_value = float(margin_summary.get("accountValue", 0))
    total_raw_usd = float(margin_summary.get("totalRawUsd", 0))
    margin_used = float(margin_summary.get("totalMarginUsed", 0))
    withdrawable = float(data.get("withdrawable", 0))

    unrealized_pnl = 0.0
    for ap in data.get("assetPositions", []):
        pos = ap.get("position", {})
        unrealized_pnl += float(pos.get("unrealizedPnl", 0))

    return BalanceResponse(
        account_value=account_value,
        total_raw_usd=total_raw_usd,
        margin_used=margin_used,
        withdrawable=withdrawable,
        unrealized_pnl=unrealized_pnl,
    )
