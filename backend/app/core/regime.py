"""Regime detection module.

Identifies market regime (bullish / bearish / neutral) using RSI on the
higher timeframe (4H by default). The regime acts as a directional filter
for the signal layer: we only take longs in bullish regime and shorts in
bearish regime.

Also provides an EMA calculation for potential trend-confirmation use.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

import numpy as np

from app.core.rsi_engine import compute_rsi_series


class Regime(str, Enum):
    """Market regime classification."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class RegimeState:
    """Snapshot of regime at a point in time."""

    regime: Regime
    rsi_value: float
    timestamp: Optional[int] = None  # unix ms, for bookkeeping

    @property
    def is_bullish(self) -> bool:
        return self.regime == Regime.BULLISH

    @property
    def is_bearish(self) -> bool:
        return self.regime == Regime.BEARISH


@dataclass
class RegimeTransition:
    """Records a change from one regime to another."""

    from_regime: Regime
    to_regime: Regime
    rsi_at_transition: float
    bar_index: int


def detect_regime(
    rsi_value: float,
    bullish_threshold: float = 55.0,
    bearish_threshold: float = 45.0,
) -> Regime:
    """Classify regime from a single RSI reading.

    Args:
        rsi_value: The RSI reading on the regime timeframe.
        bullish_threshold: RSI above this is bullish (default 55).
        bearish_threshold: RSI below this is bearish (default 45).

    Returns:
        Regime enum value.
    """
    if rsi_value >= bullish_threshold:
        return Regime.BULLISH
    if rsi_value <= bearish_threshold:
        return Regime.BEARISH
    return Regime.NEUTRAL


def compute_regime_series(
    closes: Sequence[float],
    rsi_period: int = 14,
    bullish_threshold: float = 55.0,
    bearish_threshold: float = 45.0,
) -> List[Optional[Regime]]:
    """Compute regime for every bar from a price series.

    Args:
        closes: Close prices on the regime timeframe (e.g. 4H candles).
        rsi_period: RSI period (default 14).
        bullish_threshold: Bullish threshold (default 55).
        bearish_threshold: Bearish threshold (default 45).

    Returns:
        List of Regime values. First `rsi_period` entries are None.
    """
    rsi_series = compute_rsi_series(closes, rsi_period)
    regimes: List[Optional[Regime]] = []
    for rsi in rsi_series:
        if rsi is None:
            regimes.append(None)
        else:
            regimes.append(detect_regime(rsi, bullish_threshold, bearish_threshold))
    return regimes


def detect_regime_transitions(
    regime_series: Sequence[Optional[Regime]],
) -> List[RegimeTransition]:
    """Extract all regime transitions from a series.

    Args:
        regime_series: Output of compute_regime_series.

    Returns:
        List of RegimeTransition objects recording each change.
    """
    transitions: List[RegimeTransition] = []
    prev: Optional[Regime] = None
    for i, regime in enumerate(regime_series):
        if regime is None:
            prev = None
            continue
        if prev is not None and regime != prev:
            transitions.append(
                RegimeTransition(
                    from_regime=prev,
                    to_regime=regime,
                    rsi_at_transition=0.0,  # caller can enrich if needed
                    bar_index=i,
                )
            )
        prev = regime
    return transitions


def compute_ema(values: Sequence[float], period: int) -> List[Optional[float]]:
    """Compute Exponential Moving Average over a value series.

    The EMA seed is the simple average of the first `period` values.
    The smoothing factor is alpha = 2 / (period + 1), the standard EMA formula.

    Args:
        values: Numeric series (e.g. close prices).
        period: EMA window.

    Returns:
        List of EMA values. First `period - 1` entries are None.
    """
    n = len(values)
    if n < period:
        return [None] * n

    arr = np.array(values, dtype=np.float64)
    alpha = 2.0 / (period + 1)

    result: List[Optional[float]] = [None] * (period - 1)

    # Seed with SMA of first `period` values
    ema = float(np.mean(arr[:period]))
    result.append(ema)

    for i in range(period, n):
        ema = alpha * arr[i] + (1.0 - alpha) * ema
        result.append(ema)

    return result
