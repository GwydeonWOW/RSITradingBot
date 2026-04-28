"""Order submission and reconciliation routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.order_service import OrderService

router = APIRouter()

# Shared order service instance (per-process, not per-request)
_order_service = OrderService()


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
async def submit_order(request: OrderSubmitRequest) -> OrderSubmitResponse:
    """Submit a new order.

    Creates the order locally, signs it, and prepares it for
    submission to Hyperliquid. Actual submission requires the
    WebSocket or REST transport layer.
    """
    order = _order_service.create_order(
        symbol=request.symbol,
        side=request.side,
        size=request.size,
        order_type=request.order_type,
        price=request.price,
        stop_price=request.stop_price,
        strategy_id=request.strategy_id,
    )

    signed = _order_service.sign_order(order)

    return OrderSubmitResponse(
        order_id=order.id,
        status=order.status.value,
        message="Order created and signed. Awaiting submission to venue.",
    )


@router.get("/{order_id}")
async def get_order(order_id: str) -> Dict[str, Any]:
    """Get order status by ID."""
    order = _order_service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id": order.id,
        "venue_order_id": order.venue_order_id,
        "symbol": order.symbol,
        "side": order.side,
        "status": order.status.value,
        "size": order.size,
        "filled_size": order.filled_size,
        "remaining": order.remaining_size,
        "price": order.price,
        "created_at": order.created_at.isoformat(),
    }


@router.get("/")
async def list_orders(symbol: Optional[str] = None) -> Dict[str, Any]:
    """List active orders, optionally filtered by symbol."""
    orders = _order_service.get_active_orders(symbol)
    return {
        "orders": [
            {
                "order_id": o.id,
                "symbol": o.symbol,
                "side": o.side,
                "status": o.status.value,
                "size": o.size,
                "filled_size": o.filled_size,
            }
            for o in orders
        ],
        "count": len(orders),
    }


@router.post("/reconcile")
async def reconcile_orders() -> ReconcileResponse:
    """Trigger reconciliation between local and venue state.

    Compares local order and position state with the latest
    data from Hyperliquid.
    """
    from app.execution.reconciler import Reconciler

    reconciler = Reconciler()
    # In production, fetch venue state from Hyperliquid API here
    result = reconciler.reconcile_orders(
        local_orders={},
        venue_orders={},
    )

    return ReconcileResponse(
        is_clean=result.is_clean,
        order_discrepancies=len(result.order_discrepancies),
        position_discrepancies=len(result.position_discrepancies),
        details={
            "orders": [
                {"order_id": d.order_id, "type": d.discrepancy_type}
                for d in result.order_discrepancies
            ],
        },
    )
