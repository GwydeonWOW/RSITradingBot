"""PnL and position tracking ledger.

Maintains a running ledger of realized and unrealized PnL, position
cost basis, and account-level metrics. All monetary values are in
the quote currency (USD).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PositionLedgerEntry:
    """Tracks a single position's financial state."""

    symbol: str
    side: str  # "long" or "short"
    size: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_fees: float = 0.0
    total_funding: float = 0.0
    position_cost: float = 0.0  # total cost basis

    @property
    def notional_value(self) -> float:
        return self.size * self.current_price

    def update_price(self, price: float) -> None:
        """Update current price and recalculate unrealized PnL."""
        self.current_price = price
        if self.side == "long":
            self.unrealized_pnl = self.size * (price - self.entry_price)
        else:
            self.unrealized_pnl = self.size * (self.entry_price - price)

    def add_fill(
        self,
        fill_size: float,
        fill_price: float,
        fee: float = 0.0,
        is_reduce: bool = False,
    ) -> None:
        """Process a fill (increase or reduce position).

        For opening fills (is_reduce=False), updates average entry price.
        For reducing fills (is_reduce=True), realizes PnL.

        Args:
            fill_size: Size of the fill.
            fill_price: Fill price.
            fee: Trading fee paid.
            is_reduce: Whether this reduces the position.
        """
        self.total_fees += fee

        if not is_reduce:
            # Opening / increasing position
            total_cost = self.position_cost + fill_size * fill_price
            self.size += fill_size
            self.entry_price = total_cost / self.size if self.size > 0 else 0.0
            self.position_cost = total_cost
        else:
            # Reducing / closing position
            if self.side == "long":
                realized = fill_size * (fill_price - self.entry_price)
            else:
                realized = fill_size * (self.entry_price - fill_price)
            self.realized_pnl += realized
            self.size -= fill_size
            if self.size <= 1e-10:
                self.size = 0.0
                self.position_cost = 0.0
            else:
                self.position_cost = self.size * self.entry_price

        self.update_price(fill_price)


@dataclass
class AccountLedger:
    """Account-level financial tracking."""

    equity: float = 0.0
    initial_equity: float = 0.0
    total_realized_pnl: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_fees: float = 0.0
    total_funding: float = 0.0

    # Per-symbol position tracking
    positions: Dict[str, PositionLedgerEntry] = field(default_factory=dict)

    # History of closed trades
    trade_history: List[Dict] = field(default_factory=list)

    @property
    def net_equity(self) -> float:
        """Equity including unrealized PnL."""
        return self.equity + self.total_unrealized_pnl

    @property
    def total_pnl(self) -> float:
        """Total PnL (realized + unrealized)."""
        return self.total_realized_pnl + self.total_unrealized_pnl

    @property
    def return_pct(self) -> float:
        """Total return as percentage of initial equity."""
        if self.initial_equity <= 0:
            return 0.0
        return ((self.net_equity / self.initial_equity) - 1.0) * 100

    def open_position(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        fee: float = 0.0,
    ) -> PositionLedgerEntry:
        """Open or add to a position.

        Args:
            symbol: Trading pair.
            side: "long" or "short".
            size: Position size.
            price: Entry price.
            fee: Trading fee.

        Returns:
            Updated PositionLedgerEntry.
        """
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.add_fill(size, price, fee, is_reduce=False)
        else:
            pos = PositionLedgerEntry(
                symbol=symbol,
                side=side,
                size=size,
                entry_price=price,
                current_price=price,
            )
            pos.position_cost = size * price
            pos.total_fees = fee
            self.positions[symbol] = pos

        self.equity -= fee
        self.total_fees += fee
        self._update_unrealized()
        return pos

    def reduce_position(
        self,
        symbol: str,
        size: float,
        price: float,
        fee: float = 0.0,
    ) -> Optional[Dict]:
        """Reduce or close a position.

        Args:
            symbol: Trading pair.
            size: Size to close.
            price: Exit price.
            fee: Trading fee.

        Returns:
            Trade summary dict if a position was closed, else None.
        """
        pos = self.positions.get(symbol)
        if pos is None or pos.size <= 0:
            return None

        close_size = min(size, pos.size)
        pos.add_fill(close_size, price, fee, is_reduce=True)

        self.equity += pos.realized_pnl - fee
        self.total_realized_pnl += pos.realized_pnl
        self.total_fees += fee

        trade_summary = {
            "symbol": symbol,
            "side": pos.side,
            "size": close_size,
            "entry_price": pos.entry_price,
            "exit_price": price,
            "realized_pnl": pos.realized_pnl,
            "fee": fee,
        }
        self.trade_history.append(trade_summary)

        if pos.size <= 1e-10:
            del self.positions[symbol]
        else:
            pos.realized_pnl = 0.0  # reset since we've booked it

        self._update_unrealized()
        return trade_summary

    def update_prices(self, prices: Dict[str, float]) -> None:
        """Update all position prices with latest market data.

        Args:
            prices: Dict of symbol -> current price.
        """
        for symbol, price in prices.items():
            pos = self.positions.get(symbol)
            if pos:
                pos.update_price(price)
        self._update_unrealized()

    def _update_unrealized(self) -> None:
        """Recalculate total unrealized PnL from all positions."""
        self.total_unrealized_pnl = sum(
            pos.unrealized_pnl for pos in self.positions.values()
        )
