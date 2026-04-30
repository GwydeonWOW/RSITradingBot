"""Order submission and reconciliation routes."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user
from app.core.crypto import decrypt_private_key
from app.dependencies import get_db
from app.execution.reconciler import Reconciler
from app.models.user import User
from app.models.wallet import Wallet
from app.services.order_service import OrderService

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_order_service(user: User) -> OrderService:
    """Create an OrderService scoped to the authenticated user."""
    return OrderService(user_id=user.id)


class OrderSubmitRequest(BaseModel):
    """Request body for order submission."""

    symbol: str
    side: str  # "buy" or "sell"
    size: float
    order_type: str = "market"  # "market", "limit", "stop_market"
    price: Optional[float] = None
    stop_price: Optional[float] = None
    strategy_id: Optional[str] = None


class OrderSubmitResponse(BaseModel):
    """Response after order submission."""

    order_id: str
    status: str
    message: str


class ReconcileResponse(BaseModel):
    """Reconciliation result."""

    is_clean: bool
    order_discrepancies: int
    position_discrepancies: int
    details: Dict[str, Any] = Field(default_factory=dict)


@router.post("/submit")
async def submit_order(
    request: OrderSubmitRequest,
    current_user: User = Depends(get_current_user),
) -> OrderSubmitResponse:
    """Submit a new order.

    Creates the order locally, signs it, and prepares it for
    submission to Hyperliquid. Actual submission requires the
    WebSocket or REST transport layer.
    """
    svc = _get_order_service(current_user)
    order = svc.create_order(
        symbol=request.symbol,
        side=request.side,
        size=request.size,
        order_type=request.order_type,
        price=request.price,
        stop_price=request.stop_price,
        strategy_id=request.strategy_id,
    )

    signed = svc.sign_order(order)

    return OrderSubmitResponse(
        order_id=order.id,
        status=order.status,
        message="Order created and signed. Awaiting submission to venue.",
    )


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get order status by ID."""
    svc = _get_order_service(current_user)
    order = svc.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id": order.id,
        "venue_order_id": order.venue_order_id,
        "symbol": order.symbol,
        "side": order.side,
        "status": order.status,
        "size": order.size,
        "filled_size": order.filled_size,
        "remaining": order.remaining_size,
        "price": order.price,
        "created_at": order.created_at.isoformat(),
    }


@router.get("/")
async def list_orders(
    symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List orders from DB, optionally filtered by symbol."""
    from app.models.order import Order as OrderModel
    q = select(OrderModel).where(OrderModel.user_id == current_user.id).order_by(OrderModel.created_at.desc())
    if symbol:
        q = q.where(OrderModel.symbol == symbol)
    result = await db.execute(q.limit(50))
    db_orders = result.scalars().all()
    return {
        "orders": [
            {
                "order_id": str(o.id),
                "symbol": o.symbol,
                "side": o.side,
                "status": o.status,
                "size": o.size,
                "filled_size": o.filled_size,
            }
            for o in db_orders
        ],
        "count": len(db_orders),
    }


async def _fetch_venue_orders(agent_address: str) -> Dict[str, Dict]:
    """Fetch open orders from Hyperliquid for an agent wallet."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "openOrders", "user": agent_address},
            )
            resp.raise_for_status()
            orders = resp.json()
            return {
                str(o.get("oid", "")): {
                    "status": "open",
                    "filled_size": float(o.get("sz", 0)),
                }
                for o in orders
            }
    except Exception as exc:
        logger.error("Failed to fetch venue orders for %s: %s", agent_address, exc)
        return {}


async def _fetch_venue_positions(agent_address: str) -> Dict[str, Dict]:
    """Fetch open positions from Hyperliquid for an agent wallet."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "clearinghouseState", "user": agent_address},
            )
            resp.raise_for_status()
            data = resp.json()
            asset_positions = data.get("assetPositions", [])
            result = {}
            for ap in asset_positions:
                pos = ap.get("position", {})
                coin = pos.get("coin", "")
                if coin:
                    result[coin] = {
                        "size": float(pos.get("szi", 0)),
                        "entry_price": float(pos.get("entryPx", 0)),
                    }
            return result
    except Exception as exc:
        logger.error("Failed to fetch venue positions for %s: %s", agent_address, exc)
        return {}


@router.post("/reconcile")
async def reconcile_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReconcileResponse:
    """Trigger reconciliation between local and venue state.

    Fetches current state from Hyperliquid and compares with local OMS state.
    """
    reconciler = Reconciler()

    # Build local state from OMS
    svc = _get_order_service(current_user)
    active_orders = svc.get_active_orders()
    local_orders = {
        o.id: {"status": o.status, "filled_size": o.filled_size}
        for o in active_orders
    }

    # Fetch active wallet for venue state
    wallet_result = await db.execute(
        select(Wallet).where(
            Wallet.user_id == current_user.id,
            Wallet.is_active.is_(True),
        ).limit(1)
    )
    wallet = wallet_result.scalar_one_or_none()

    venue_orders: Dict[str, Dict] = {}
    venue_positions: Dict[str, Dict] = {}

    if wallet:
        query_address = wallet.master_address or wallet.agent_address
        venue_orders = await _fetch_venue_orders(query_address)
        venue_positions = await _fetch_venue_positions(query_address)

    order_result = reconciler.reconcile_orders(
        local_orders=local_orders,
        venue_orders=venue_orders,
    )

    return ReconcileResponse(
        is_clean=order_result.is_clean,
        order_discrepancies=len(order_result.order_discrepancies),
        position_discrepancies=len(order_result.position_discrepancies),
        details={
            "orders": [
                {
                    "order_id": d.order_id,
                    "local_status": d.local_status,
                    "venue_status": d.venue_status,
                    "type": d.discrepancy_type,
                }
                for d in order_result.order_discrepancies
            ],
            "local_active_orders": len(local_orders),
            "venue_open_orders": len(venue_orders),
        },
    )
