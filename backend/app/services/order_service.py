"""Order service.

Business logic for order submission, status tracking, and
coordination between the OMS, signer, and reconciliation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.execution.oms import (
    OMSOrder,
    OMSOrderStatus,
    OrderManagementSystem,
)
from app.execution.signer import HyperliquidSigner

logger = logging.getLogger(__name__)


class OrderService:
    """High-level order management facade.

    Coordinates order creation, signing, submission, and tracking.

    Usage:
        service = OrderService(signer=signer)
        order = service.create_and_submit(
            symbol="BTC", side="buy", size=0.01,
            order_type="market"
        )
    """

    def __init__(
        self,
        signer: Optional[HyperliquidSigner] = None,
    ) -> None:
        self._oms = OrderManagementSystem()
        self._signer = signer

    def create_order(
        self,
        symbol: str,
        side: str,
        size: float,
        order_type: str = "market",
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        strategy_id: Optional[str] = None,
    ) -> OMSOrder:
        """Create a new order in INTENT state.

        Args:
            symbol: Trading pair.
            side: "buy" or "sell".
            size: Order size.
            order_type: "market", "limit", "stop_market", "stop_limit".
            price: Limit price.
            stop_price: Stop trigger price.
            strategy_id: Associated strategy ID.

        Returns:
            The created order.
        """
        order = self._oms.create_order(
            symbol=symbol,
            side=side,
            size=size,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            strategy_id=strategy_id,
        )
        return order

    def sign_order(self, order: OMSOrder) -> Optional[Dict[str, Any]]:
        """Sign an order for submission to the venue.

        Args:
            order: The order to sign.

        Returns:
            Signed payload dict, or None if signer is not configured.
        """
        if self._signer is None:
            logger.warning("No signer configured, cannot sign order %s", order.id)
            return None

        hl_order_type = "Ioc"
        if order.order_type == "limit":
            hl_order_type = "Gtc"

        signed = self._signer.sign_order(
            symbol=order.symbol,
            side=order.side,
            size=order.size,
            price=order.price,
            order_type=hl_order_type,
            reduce_only=order.order_type == "stop_market",
        )
        return signed.payload

    def accept_order(self, order_id: str, venue_order_id: str) -> OMSOrder:
        """Mark an order as accepted by the venue.

        Args:
            order_id: Local order ID.
            venue_order_id: Venue-assigned order ID.

        Returns:
            Updated order.
        """
        return self._oms.transition(
            order_id, OMSOrderStatus.ACCEPTED, venue_order_id=venue_order_id
        )

    def fill_order(
        self, order_id: str, filled_size: float, is_complete: bool = False
    ) -> OMSOrder:
        """Report a fill on an order.

        Args:
            order_id: Local order ID.
            filled_size: Total filled size so far.
            is_complete: Whether this is the final fill.

        Returns:
            Updated order.
        """
        if is_complete:
            return self._oms.transition(
                order_id, OMSOrderStatus.FILLED, filled_size=filled_size
            )
        return self._oms.transition(
            order_id, OMSOrderStatus.FILLING, filled_size=filled_size
        )

    def cancel_order(self, order_id: str) -> OMSOrder:
        """Cancel an order.

        Args:
            order_id: Local order ID.

        Returns:
            Canceled order.
        """
        return self._oms.cancel_order(order_id)

    def get_order(self, order_id: str) -> Optional[OMSOrder]:
        """Get an order by ID."""
        return self._oms.get_order(order_id)

    def get_active_orders(self, symbol: Optional[str] = None) -> List[OMSOrder]:
        """Get all active (non-terminal) orders."""
        return self._oms.get_active_orders(symbol)

    @property
    def oms(self) -> OrderManagementSystem:
        """Access the underlying OMS for advanced operations."""
        return self._oms
