"""Risk management module.

Handles position sizing, exposure limits, and Value-at-Risk calculations
to enforce disciplined risk management across the trading system.

Key responsibilities:
- Position sizing via quarter-Kelly or fixed fractional method.
- Max leverage enforcement (capped at 3x).
- Max total exposure as a percentage of equity.
- VaR calculation (historical and parametric).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from app.core.signal import SignalType


@dataclass(frozen=True)
class PositionSizing:
    """Result of a position sizing calculation."""

    size_notional: float  # position size in quote currency
    size_contracts: float  # position size in contracts/coins
    leverage: int
    risk_amount: float  # amount of equity risked on this trade
    risk_pct: float  # risk as fraction of equity

    @property
    def margin_required(self) -> float:
        """Margin needed to open this position."""
        return self.size_notional / self.leverage if self.leverage > 0 else 0.0


@dataclass(frozen=True)
class VaRResult:
    """Value-at-Risk calculation output."""

    var_95: float  # 95% confidence VaR
    var_99: float  # 99% confidence VaR
    cvar_95: float  # Expected Shortfall (CVaR) at 95%
    method: str  # "historical" or "parametric"


class RiskManager:
    """Central risk manager for position sizing and exposure control.

    Usage:
        rm = RiskManager(equity=10000, max_leverage=3)
        sizing = rm.calculate_position_size(
            entry_price=50000, stop_price=49500,
            direction=SignalType.LONG, win_rate=0.55,
            avg_win_loss_ratio=1.8
        )
    """

    def __init__(
        self,
        equity: float,
        max_leverage: int = 3,
        risk_per_trade_min: float = 0.0025,
        risk_per_trade_max: float = 0.0075,
        max_total_exposure_pct: float = 0.30,
        default_risk_pct: float = 0.005,
    ) -> None:
        self._equity = equity
        self._max_leverage = max_leverage
        self._risk_per_trade_min = risk_per_trade_min
        self._risk_per_trade_max = risk_per_trade_max
        self._max_total_exposure_pct = max_total_exposure_pct
        self._default_risk_pct = default_risk_pct

    @property
    def equity(self) -> float:
        return self._equity

    @equity.setter
    def equity(self, value: float) -> None:
        self._equity = value

    @property
    def max_total_notional(self) -> float:
        """Maximum total notional exposure allowed."""
        return self._equity * self._max_total_exposure_pct * self._max_leverage

    def calculate_position_size(
        self,
        entry_price: float,
        stop_price: float,
        direction: SignalType,
        current_exposure: float = 0.0,
        win_rate: Optional[float] = None,
        avg_win_loss_ratio: Optional[float] = None,
        method: str = "fixed_fractional",
    ) -> PositionSizing:
        """Calculate position size based on risk parameters.

        Supports two sizing methods:
        - "fixed_fractional": risk a fixed percentage of equity per trade.
        - "quarter_kelly": use quarter-Kelly criterion based on win rate and W/L ratio.

        Args:
            entry_price: Planned entry price.
            stop_price: Stop-loss price.
            direction: Trade direction (LONG or SHORT).
            current_exposure: Current total notional exposure.
            win_rate: Historical win rate (for Kelly sizing).
            avg_win_loss_ratio: Average win/loss ratio (for Kelly sizing).
            method: "fixed_fractional" or "quarter_kelly".

        Returns:
            PositionSizing with size and risk details.
        """
        risk_distance = abs(entry_price - stop_price)
        if risk_distance <= 0:
            return PositionSizing(0.0, 0.0, 1, 0.0, 0.0)

        # Determine risk percentage
        if method == "quarter_kelly" and win_rate is not None and avg_win_loss_ratio is not None:
            risk_pct = self._quarter_kelly_risk(win_rate, avg_win_loss_ratio)
        else:
            risk_pct = self._default_risk_pct

        # Clamp risk to allowed range
        risk_pct = max(self._risk_per_trade_min, min(self._risk_per_trade_max, risk_pct))

        # Calculate risk amount in quote currency
        risk_amount = self._equity * risk_pct

        # Position size in quote (notional)
        size_notional = (risk_amount / risk_distance) * entry_price

        # Check exposure limit
        remaining_exposure = self.max_total_notional - current_exposure
        if size_notional > remaining_exposure:
            size_notional = max(0.0, remaining_exposure)

        # Determine leverage needed (1x if equity covers notional)
        leverage = 1
        if size_notional > self._equity:
            leverage = min(
                self._max_leverage,
                int(np.ceil(size_notional / self._equity)),
            )

        # Recalculate actual risk based on final size
        actual_risk = (size_notional / entry_price) * risk_distance

        size_contracts = size_notional / entry_price

        return PositionSizing(
            size_notional=size_notional,
            size_contracts=size_contracts,
            leverage=leverage,
            risk_amount=actual_risk,
            risk_pct=actual_risk / self._equity if self._equity > 0 else 0.0,
        )

    def _quarter_kelly_risk(self, win_rate: float, avg_win_loss_ratio: float) -> float:
        """Calculate risk percentage using quarter-Kelly criterion.

        Full Kelly fraction: f* = (p * b - q) / b
        where p = win_rate, q = 1 - win_rate, b = avg_win_loss_ratio.
        Quarter-Kelly uses f* / 4 for conservative sizing.

        Returns:
            Risk percentage as a fraction (e.g. 0.005 for 0.5%).
        """
        p = win_rate
        q = 1.0 - win_rate
        b = avg_win_loss_ratio

        if b <= 0:
            return self._risk_per_trade_min

        kelly_full = (p * b - q) / b
        if kelly_full <= 0:
            return self._risk_per_trade_min

        kelly_quarter = kelly_full / 4.0
        return kelly_quarter

    def check_exposure_limit(
        self,
        new_notional: float,
        current_exposure: float,
    ) -> bool:
        """Check if adding a new position would exceed exposure limits.

        Args:
            new_notional: Notional value of the proposed new position.
            current_exposure: Current total notional exposure.

        Returns:
            True if the trade is allowed, False if it would breach limits.
        """
        return (current_exposure + new_notional) <= self.max_total_notional

    @staticmethod
    def calculate_historical_var(
        returns: Sequence[float],
        confidence_levels: Tuple[float, ...] = (0.95, 0.99),
    ) -> VaRResult:
        """Calculate historical VaR from a series of returns.

        Uses the empirical distribution of returns (no distributional
        assumptions).

        Args:
            returns: Historical PnL returns as fractions (e.g. 0.01 for 1%).
            confidence_levels: Confidence levels for VaR calculation.

        Returns:
            VaRResult with VaR at specified confidence levels and CVaR.
        """
        arr = np.array(returns, dtype=np.float64)
        if len(arr) < 10:
            return VaRResult(var_95=0.0, var_99=0.0, cvar_95=0.0, method="historical")

        sorted_returns = np.sort(arr)
        n = len(sorted_returns)

        var_95 = float(-np.percentile(sorted_returns, (1.0 - 0.95) * 100))
        var_99 = float(-np.percentile(sorted_returns, (1.0 - 0.99) * 100))

        # CVaR (Expected Shortfall) at 95%: mean of returns below VaR
        cutoff_95 = int(np.floor(n * 0.05))
        if cutoff_95 > 0:
            cvar_95 = float(-np.mean(sorted_returns[:cutoff_95]))
        else:
            cvar_95 = var_95

        return VaRResult(var_95=var_95, var_99=var_99, cvar_95=cvar_95, method="historical")

    @staticmethod
    def calculate_parametric_var(
        returns: Sequence[float],
        confidence_levels: Tuple[float, ...] = (0.95, 0.99),
    ) -> VaRResult:
        """Calculate parametric (variance-covariance) VaR.

        Assumes returns are normally distributed.

        Args:
            returns: Historical PnL returns as fractions.
            confidence_levels: Confidence levels.

        Returns:
            VaRResult assuming normal distribution.
        """
        from scipy.stats import norm

        arr = np.array(returns, dtype=np.float64)
        if len(arr) < 2:
            return VaRResult(var_95=0.0, var_99=0.0, cvar_95=0.0, method="parametric")

        mu = float(np.mean(arr))
        sigma = float(np.std(arr, ddof=1))

        var_95 = -(mu - norm.ppf(0.95) * sigma)
        var_99 = -(mu - norm.ppf(0.99) * sigma)

        # CVaR for normal: mu - sigma * (phi(z_alpha) / alpha)
        z_95 = norm.ppf(0.95)
        cvar_95 = -(mu - sigma * (norm.pdf(z_95) / 0.05))

        return VaRResult(
            var_95=float(var_95),
            var_99=float(var_99),
            cvar_95=float(cvar_95),
            method="parametric",
        )
