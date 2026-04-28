# Bug fix applied:
# - _rsi_from_averages now returns 50.0 (neutral) when both avg_gain and avg_loss
#   are zero (flat prices), instead of incorrectly returning 100.0.
"""RSI calculation engine with Wilder's smoothing method.

Implements the standard RSI as defined by J. Welles Wilder Jr. in
"New Concepts in Technical Trading Systems" (1978).

Key details:
- Uses Wilder's exponential smoothing (alpha = 1/period), not simple SMA.
- For the first `period` bars, uses simple averaging to seed the initial
  average gain / average loss values.
- Handles the edge case where average_loss approaches zero, capping RSI at 100.
- Returns not just RSI but also avg_gain and avg_loss so callers can continue
  the smoothing chain incrementally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np


@dataclass(frozen=True)
class RSIResult:
    """Output of an RSI calculation."""

    rsi: float
    avg_gain: float
    avg_loss: float
    period: int

    @property
    def is_overbought(self) -> bool:
        return self.rsi >= 70.0

    @property
    def is_oversold(self) -> bool:
        return self.rsi <= 30.0


def compute_rsi(
    closes: Sequence[float],
    period: int = 14,
    prior_avg_gain: Optional[float] = None,
    prior_avg_loss: Optional[float] = None,
) -> Optional[RSIResult]:
    """Calculate RSI from a sequence of closing prices.

    Supports two modes:
    1. Full calculation: pass a list of closes with length >= period + 1.
       Returns RSI computed from the entire sequence.
    2. Incremental update: pass the last bar's close in a length-1 sequence
       along with prior_avg_gain and prior_avg_loss. Returns the updated RSI.

    Args:
        closes: Sequence of close prices. Must have length >= 1 for incremental,
                or >= period + 1 for a full calculation.
        period: RSI period (default 14).
        prior_avg_gain: Previous average gain for incremental mode.
        prior_avg_loss: Previous average loss for incremental mode.

    Returns:
        RSIResult with rsi, avg_gain, avg_loss, and period.
        Returns None if insufficient data.
    """
    if len(closes) < 2 and prior_avg_gain is None:
        return None

    # Incremental update: one new close, prior averages provided
    if prior_avg_gain is not None and prior_avg_loss is not None and len(closes) >= 2:
        change = closes[-1] - closes[-2]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (prior_avg_gain * (period - 1) + gain) / period
        avg_loss = (prior_avg_loss * (period - 1) + loss) / period
        rsi = _rsi_from_averages(avg_gain, avg_loss)
        return RSIResult(rsi=rsi, avg_gain=avg_gain, avg_loss=avg_loss, period=period)

    # Full calculation: need at least period + 1 prices
    if len(closes) < period + 1:
        return None

    prices = np.array(closes, dtype=np.float64)
    deltas = np.diff(prices)

    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Seed: simple average of first `period` changes
    avg_gain: float = float(np.mean(gains[:period]))
    avg_loss: float = float(np.mean(losses[:period]))

    # Wilder smoothing for subsequent values
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    rsi = _rsi_from_averages(avg_gain, avg_loss)
    return RSIResult(rsi=rsi, avg_gain=avg_gain, avg_loss=avg_loss, period=period)


def compute_rsi_series(
    closes: Sequence[float],
    period: int = 14,
) -> List[Optional[float]]:
    """Compute RSI for every bar from period onward.

    Returns a list of the same length as closes. The first `period` entries
    will be None (insufficient data). Each subsequent entry is the RSI value
    at that bar.

    This is useful for backtesting where you need the full historical RSI
    series rather than just the latest value.

    Args:
        closes: Sequence of close prices.
        period: RSI period (default 14).

    Returns:
        List of floats (or None for the warmup period).
    """
    n = len(closes)
    if n < period + 1:
        return [None] * n

    prices = np.array(closes, dtype=np.float64)
    deltas = np.diff(prices)

    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    result: List[Optional[float]] = [None] * (period)

    # Seed with simple average
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    result.append(_rsi_from_averages(avg_gain, avg_loss))

    # Wilder smoothing for the rest
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        result.append(_rsi_from_averages(avg_gain, avg_loss))

    return result


def compute_rsi_with_state(
    closes: Sequence[float],
    period: int = 14,
) -> Tuple[List[Optional[float]], Optional[float], Optional[float]]:
    """Compute full RSI series and return final avg_gain / avg_loss for chaining.

    This is the primary function for streaming / real-time use where you
    need the series *and* want to continue calculating incrementally.

    Args:
        closes: Sequence of close prices.
        period: RSI period.

    Returns:
        Tuple of (rsi_series, final_avg_gain, final_avg_loss).
        The series has the same length as closes; first `period` are None.
    """
    series = compute_rsi_series(closes, period)
    if len(closes) < period + 1:
        return series, None, None

    # Recompute the final averages by running the smoothing to the end
    prices = np.array(closes, dtype=np.float64)
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    return series, avg_gain, avg_loss


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    """Convert average gain and loss to RSI value.

    Handles the edge case where avg_loss is zero (RSI = 100).
    """
    if avg_gain < 1e-10 and avg_loss < 1e-10:
        return 50.0
    if avg_loss < 1e-10:
        return 100.0
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # Clamp to [0, 100] for floating-point safety
    return max(0.0, min(100.0, rsi))
