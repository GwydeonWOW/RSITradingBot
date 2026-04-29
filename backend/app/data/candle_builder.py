"""Candle builder module.

Aggregates raw tick data into OHLCV candles for configurable timeframes.
Supports the timeframes used by the RSI strategy: 15m, 1h, and 4h.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class Candle:
    """A single OHLCV candle."""

    timestamp: int  # open time in unix ms
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    trade_count: int = 0
    is_closed: bool = False


# Timeframe to millisecond duration
TIMEFRAME_MS = {
    "1m": 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
}


class CandleBuilder:
    """Builds candles from a stream of tick updates.

    Maintains partial candles for each timeframe and emits completed
    candles when the time window closes.

    Usage:
        builder = CandleBuilder(timeframes=["15m", "1h", "4h"])
        builder.on_tick(timestamp=1714000000000, price=50000.0, size=0.1)
        candles = builder.flush_closed()
    """

    def __init__(self, timeframes: Optional[List[str]] = None) -> None:
        self._timeframes = timeframes or ["15m", "1h", "4h"]
        self._active: Dict[str, Candle] = {}
        self._closed: Dict[str, List[Candle]] = {tf: [] for tf in self._timeframes}

    def on_tick(self, timestamp: int, price: float, size: float = 0.0) -> None:
        """Process a tick update and update all timeframe candles.

        Args:
            timestamp: Unix ms timestamp of the tick.
            price: Trade price.
            size: Trade size.
        """
        for tf in self._timeframes:
            tf_ms = TIMEFRAME_MS.get(tf)
            if tf_ms is None:
                continue

            # Calculate the candle open time for this tick
            candle_open_ts = (timestamp // tf_ms) * tf_ms

            active = self._active.get(tf)

            # Check if we need to close the current candle and start a new one
            if active is not None and active.timestamp != candle_open_ts:
                active.is_closed = True
                self._closed[tf].append(active)
                active = None

            if active is None:
                active = Candle(
                    timestamp=candle_open_ts,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=size,
                    trade_count=1,
                )
                self._active[tf] = active
            else:
                active.high = max(active.high, price)
                active.low = min(active.low, price)
                active.close = price
                active.volume += size
                active.trade_count += 1

    def flush_closed(self) -> Dict[str, List[Candle]]:
        """Return all closed candles and clear the closed buffers.

        Returns:
            Dict mapping timeframe to list of closed Candle objects.
        """
        result = {tf: list(candles) for tf, candles in self._closed.items()}
        self._closed = {tf: [] for tf in self._timeframes}
        return result

    def get_active(self, timeframe: str) -> Optional[Candle]:
        """Get the current active (incomplete) candle for a timeframe."""
        return self._active.get(timeframe)

    def close_all(self, timestamp: int) -> Dict[str, List[Candle]]:
        """Force-close all active candles at the given timestamp.

        Useful at shutdown or end of data to flush remaining candles.

        Args:
            timestamp: Timestamp to assign as the close marker.

        Returns:
            Dict mapping timeframe to closed Candle objects.
        """
        for tf, candle in self._active.items():
            candle.is_closed = True
            self._closed[tf].append(candle)
        self._active = {}
        return self.flush_closed()


def ticks_to_dataframe(ticks: List[Dict]) -> pd.DataFrame:
    """Convert a list of tick dicts to a sorted DataFrame.

    Args:
        ticks: List of dicts with keys: timestamp, price, size, side.

    Returns:
        DataFrame sorted by timestamp.
    """
    if not ticks:
        return pd.DataFrame(columns=["timestamp", "price", "size", "side"])
    df = pd.DataFrame(ticks)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def resample_candles(
    df: pd.DataFrame,
    source_tf: str,
    target_tf: str,
) -> pd.DataFrame:
    """Resample candles from one timeframe to a higher one.

    Args:
        df: DataFrame with columns: timestamp, open, high, low, close, volume.
        source_tf: Source timeframe string (e.g. "15m").
        target_tf: Target timeframe string (e.g. "1h").

    Returns:
        Resampled DataFrame with OHLCV columns.
    """
    if df.empty:
        return df

    source_ms = TIMEFRAME_MS.get(source_tf, 0)
    target_ms = TIMEFRAME_MS.get(target_tf, 0)
    if source_ms == 0 or target_ms == 0 or target_ms <= source_ms:
        return df

    # Calculate the target candle each source candle belongs to
    df = df.copy()
    df["target_open"] = (df["timestamp"] // target_ms) * target_ms

    result = df.groupby("target_open").agg(
        timestamp=("target_open", "first"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    ).reset_index(drop=True)

    return result
