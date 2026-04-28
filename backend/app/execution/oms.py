# Bug fix applied:
# - Added ACCEPTED -> CANCELED state transition to allow canceling orders
#   after they have been accepted by the venue.
"""Order Management System.

Tracks order lifecycle through states:
  intent -> accepted -> resting/filling -> terminal (filled, canceled, rejected, expired)

Provides a state machine that enforces valid transitions and prevents
illegal state changes (e.g. filling a canceled order).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class OMSOrderStatus(str, Enum):
    """Order lifecycle states."""

    INTENT = "intent"          # Created locally, not yet sent to venue
    ACCEPTED = "accepted"      # Acknowledged by venue
    RESTING = "resting"        # Limit order sitting on the book
    FILLING = "filling"        # Partially filled
    FILLED = "filled"          # Fully filled (terminal)
    CANCELED = "canceled"      # Canceled (terminal)
    REJECTED = "rejected"      # Rejected by venue (terminal)
    EXPIRED = "expired"        # Time-in-force expired (terminal)


# Valid state transitions
TRANSITIONS: Dict[OMSOrderStatus, List[OMSOrderStatus]] = {
    OMSOrderStatus.INTENT: [OMSOrderStatus.ACCEPTED, OMSOrderStatus.REJECTED, OMSOrderStatus.CANCELED],
    OMSOrderStatus.ACCEPTED: [OMSOrderStatus.RESTING, OMSOrderStatus.FILLING, OMSOrderStatus.REJECTED, OMSOrderStatus.CANCELED],
    OMSOrderStatus.RESTING: [OMSOrderStatus.FILLING, OMSOrderStatus.CANCELED, OMSOrderStatus.EXPIRED],
    OMSOrderStatus.FILLING: [OMSOrderStatus.FILLED, OMSOrderStatus.CANCELED],
    OMSOrderStatus.FILLED: [],
    OMSOrderStatus.CANCELED: [],
    OMSOrderStatus.REJECTED: [],
    OMSOrderStatus.EXPIRED: [],
}

TERMINAL_STATES = {
    OMSOrderStatus.FILLED,
    OMSOrderStatus.CANCELED,
    OMSOrderStatus.REJECTED,
    OMSOrderStatus.EXPIRED,
}


class InvalidTransitionError(Exception):
    """Raised when an invalid order state transition is attempted."""
    pass


@dataclass
class OMSOrder:
    """Order tracked by the OMS."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    venue_order_id: Optional[str] = None
    symbol: str = ""
    side: str = ""  # "buy" or "sell"
    order_type: str = ""  # "market", "limit", etc.
    status: OMSOrderStatus = OMSOrderStatus.INTENT

    size: float = 0.0
    filled_size: float = 0.0
    price: Optional[float] = None
    stop_price: Optional[float] = None

    strategy_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATES

    @property
    def remaining_size(self) -> float:
        return self.size - self.filled_size

    @property
    def fill_pct(self) -> float:
        return self.filled_size / self.size if self.size > 0 else 0.0


class OrderManagementSystem:
    """In-memory order state machine.

    Usage:
        oms = OrderManagementSystem()
        order = oms.create_order(symbol="BTC", side="buy", size=0.1, order_type="market")
        oms.transition(order.id, OMSOrderStatus.ACCEPTED)
        oms.transition(order.id, OMSOrderStatus.FILLING, filled_size=0.05)
        oms.transition(order.id, OMSOrderStatus.FILLED, filled_size=0.1)
    """

    def __init__(self) -> None:
        self._orders: Dict[str, OMSOrder] = {}

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
            order_type: "market", "limit", etc.
            price: Limit price (for limit orders).
            stop_price: Stop trigger price.
            strategy_id: Associated strategy.

        Returns:
            The created OMSOrder.
        """
        order = OMSOrder(
            symbol=symbol,
            side=side,
            size=size,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            strategy_id=strategy_id,
        )
        self._orders[order.id] = order
        logger.info("Order created: %s %s %s %s", order.id, side, size, symbol)
        return order

    def transition(
        self,
        order_id: str,
        new_status: OMSOrderStatus,
        venue_order_id: Optional[str] = None,
        filled_size: Optional[float] = None,
    ) -> OMSOrder:
        """Transition an order to a new status.

        Args:
            order_id: Order to transition.
            new_status: Target status.
            venue_order_id: Venue-assigned order ID (for accepted state).
            filled_size: Updated filled size (for filling transitions).

        Returns:
            The updated OMSOrder.

        Raises:
            InvalidTransitionError: If the transition is not valid.
            KeyError: If the order_id is not found.
        """
        order = self._orders.get(order_id)
        if order is None:
            raise KeyError(f"Order {order_id} not found")

        if new_status not in TRANSITIONS.get(order.status, []):
            raise InvalidTransitionError(
                f"Cannot transition order {order_id} from {order.status.value} "
                f"to {new_status.value}"
            )

        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()

        if venue_order_id is not None:
            order.venue_order_id = venue_order_id

        if filled_size is not None:
            order.filled_size = filled_size

        logger.info(
            "Order %s: %s -> %s (filled: %.4f/%.4f)",
            order_id, old_status.value, new_status.value,
            order.filled_size, order.size,
        )
        return order

    def get_order(self, order_id: str) -> Optional[OMSOrder]:
        """Get an order by ID."""
        return self._orders.get(order_id)

    def get_active_orders(self, symbol: Optional[str] = None) -> List[OMSOrder]:
        """Get all non-terminal orders, optionally filtered by symbol."""
        orders = [o for o in self._orders.values() if not o.is_terminal]
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    def get_orders_by_status(self, status: OMSOrderStatus) -> List[OMSOrder]:
        """Get all orders in a specific status."""
        return [o for o in self._orders.values() if o.status == status]

    def cancel_order(self, order_id: str) -> OMSOrder:
        """Cancel an order.

        Args:
            order_id: Order to cancel.

        Returns:
            The canceled order.

        Raises:
            InvalidTransitionError: If the order cannot be canceled.
        """
        return self.transition(order_id, OMSOrderStatus.CANCELED)

    @property
    def order_count(self) -> int:
        return len(self._orders)

    @property
    def active_count(self) -> int:
        return len([o for o in self._orders.values() if not o.is_terminal])
