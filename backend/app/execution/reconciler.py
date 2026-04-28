"""Reconciliation service.

Compares local order and position state with the venue's reported
state to detect discrepancies (missed fills, stale orders, position
mismatches). Essential for maintaining accurate accounting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrderDiscrepancy:
    """A mismatch between local and venue order state."""

    order_id: str
    local_status: str
    venue_status: str
    local_filled: float
    venue_filled: float
    discrepancy_type: str  # "status_mismatch", "fill_mismatch", "missing_locally", "missing_venue"


@dataclass(frozen=True)
class PositionDiscrepancy:
    """A mismatch between local and venue position state."""

    symbol: str
    local_size: float
    venue_size: float
    local_entry: float
    venue_entry: float
    discrepancy_type: str  # "size_mismatch", "entry_mismatch", "missing_locally", "missing_venue"


@dataclass
class ReconciliationResult:
    """Output of a reconciliation run."""

    timestamp: int
    order_discrepancies: List[OrderDiscrepancy] = field(default_factory=list)
    position_discrepancies: List[PositionDiscrepancy] = field(default_factory=list)
    is_clean: bool = True

    def __post_init__(self) -> None:
        self.is_clean = not self.order_discrepancies and not self.position_discrepancies


class Reconciler:
    """Compares local state with venue state and reports discrepancies.

    Usage:
        reconciler = Reconciler()
        result = reconciler.reconcile_orders(local_orders, venue_orders)
        if not result.is_clean:
            for d in result.order_discrepancies:
                logger.warning("Discrepancy: %s", d)
    """

    def reconcile_orders(
        self,
        local_orders: Dict[str, Dict],
        venue_orders: Dict[str, Dict],
    ) -> ReconciliationResult:
        """Reconcile local order state with venue order state.

        Args:
            local_orders: Dict of order_id -> {"status": str, "filled_size": float}
            venue_orders: Dict of order_id -> {"status": str, "filled_size": float}

        Returns:
            ReconciliationResult listing any discrepancies found.
        """
        import time
        discrepancies: List[OrderDiscrepancy] = []

        local_ids = set(local_orders.keys())
        venue_ids = set(venue_orders.keys())

        # Orders missing on venue (locally tracked but venue doesn't know)
        for oid in local_ids - venue_ids:
            local = local_orders[oid]
            if local.get("status") not in ("filled", "canceled", "expired", "rejected"):
                discrepancies.append(OrderDiscrepancy(
                    order_id=oid,
                    local_status=local.get("status", "unknown"),
                    venue_status="missing",
                    local_filled=local.get("filled_size", 0.0),
                    venue_filled=0.0,
                    discrepancy_type="missing_venue",
                ))

        # Orders missing locally (venue has them but we don't)
        for oid in venue_ids - local_ids:
            venue = venue_orders[oid]
            discrepancies.append(OrderDiscrepancy(
                order_id=oid,
                local_status="missing",
                venue_status=venue.get("status", "unknown"),
                local_filled=0.0,
                venue_filled=venue.get("filled_size", 0.0),
                discrepancy_type="missing_locally",
            ))

        # Compare overlapping orders
        for oid in local_ids & venue_ids:
            local = local_orders[oid]
            venue = venue_orders[oid]

            # Status mismatch
            if local.get("status") != venue.get("status"):
                discrepancies.append(OrderDiscrepancy(
                    order_id=oid,
                    local_status=local.get("status", "unknown"),
                    venue_status=venue.get("status", "unknown"),
                    local_filled=local.get("filled_size", 0.0),
                    venue_filled=venue.get("filled_size", 0.0),
                    discrepancy_type="status_mismatch",
                ))

            # Fill mismatch
            local_filled = local.get("filled_size", 0.0)
            venue_filled = venue.get("filled_size", 0.0)
            if abs(local_filled - venue_filled) > 1e-8:
                discrepancies.append(OrderDiscrepancy(
                    order_id=oid,
                    local_status=local.get("status", "unknown"),
                    venue_status=venue.get("status", "unknown"),
                    local_filled=local_filled,
                    venue_filled=venue_filled,
                    discrepancy_type="fill_mismatch",
                ))

        return ReconciliationResult(
            timestamp=int(time.time() * 1000),
            order_discrepancies=discrepancies,
        )

    def reconcile_positions(
        self,
        local_positions: Dict[str, Dict],
        venue_positions: Dict[str, Dict],
    ) -> ReconciliationResult:
        """Reconcile local position state with venue position state.

        Args:
            local_positions: Dict of symbol -> {"size": float, "entry_price": float}
            venue_positions: Dict of symbol -> {"size": float, "entry_price": float}

        Returns:
            ReconciliationResult listing any position discrepancies.
        """
        import time
        discrepancies: List[PositionDiscrepancy] = []

        local_symbols = set(local_positions.keys())
        venue_symbols = set(venue_positions.keys())

        # Positions missing on venue
        for sym in local_symbols - venue_symbols:
            local = local_positions[sym]
            if abs(local.get("size", 0.0)) > 1e-8:
                discrepancies.append(PositionDiscrepancy(
                    symbol=sym,
                    local_size=local.get("size", 0.0),
                    venue_size=0.0,
                    local_entry=local.get("entry_price", 0.0),
                    venue_entry=0.0,
                    discrepancy_type="missing_venue",
                ))

        # Positions missing locally
        for sym in venue_symbols - local_symbols:
            venue = venue_positions[sym]
            if abs(venue.get("size", 0.0)) > 1e-8:
                discrepancies.append(PositionDiscrepancy(
                    symbol=sym,
                    local_size=0.0,
                    venue_size=venue.get("size", 0.0),
                    local_entry=0.0,
                    venue_entry=venue.get("entry_price", 0.0),
                    discrepancy_type="missing_locally",
                ))

        # Compare overlapping positions
        for sym in local_symbols & venue_symbols:
            local = local_positions[sym]
            venue = venue_positions[sym]

            local_size = local.get("size", 0.0)
            venue_size = venue.get("size", 0.0)

            if abs(local_size - venue_size) > 1e-8:
                discrepancies.append(PositionDiscrepancy(
                    symbol=sym,
                    local_size=local_size,
                    venue_size=venue_size,
                    local_entry=local.get("entry_price", 0.0),
                    venue_entry=venue.get("entry_price", 0.0),
                    discrepancy_type="size_mismatch",
                ))

        return ReconciliationResult(
            timestamp=int(time.time() * 1000),
            position_discrepancies=discrepancies,
        )
