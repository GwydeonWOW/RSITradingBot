"""Market data recorder.

Persists incoming market data to both a local Parquet file store and
the time-series database (ClickHouse/TimescaleDB). This dual write
ensures data durability and enables fast local backtesting from Parquet.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MarketDataRecorder:
    """Records market data to Parquet files and optionally to a database.

    Parquet files are organized by date and symbol under a root data
    directory, making it easy to load historical data for backtests.

    Directory layout:
        data/
          candles/
            BTC/
              2024-01-01.parquet
              2024-01-02.parquet
            ETH/
              ...
          ticks/
            BTC/
              2024-01-01.parquet
    """

    def __init__(
        self,
        data_dir: str = "data",
        buffer_size: int = 1000,
    ) -> None:
        self._data_dir = Path(data_dir)
        self._buffer_size = buffer_size
        self._candle_buffer: Dict[str, List[Dict[str, Any]]] = {}
        self._tick_buffer: Dict[str, List[Dict[str, Any]]] = {}

    def record_candle(
        self,
        symbol: str,
        timestamp: int,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        timeframe: str = "15m",
    ) -> None:
        """Buffer a candle data point for later flush to Parquet.

        Args:
            symbol: Trading pair (e.g. "BTC").
            timestamp: Unix ms timestamp of candle open.
            open, high, low, close, volume: OHLCV data.
            timeframe: Candle timeframe (e.g. "15m", "1h", "4h").
        """
        key = f"{symbol}_{timeframe}"
        if key not in self._candle_buffer:
            self._candle_buffer[key] = []

        self._candle_buffer[key].append({
            "timestamp": timestamp,
            "open": open,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "timeframe": timeframe,
            "symbol": symbol,
        })

        if len(self._candle_buffer[key]) >= self._buffer_size:
            self.flush_candles(key)

    def record_tick(
        self,
        symbol: str,
        timestamp: int,
        price: float,
        size: float,
        side: str,
    ) -> None:
        """Buffer a tick/trade data point."""
        if symbol not in self._tick_buffer:
            self._tick_buffer[symbol] = []

        self._tick_buffer[symbol].append({
            "timestamp": timestamp,
            "price": price,
            "size": size,
            "side": side,
            "symbol": symbol,
        })

        if len(self._tick_buffer[symbol]) >= self._buffer_size:
            self.flush_ticks(symbol)

    def flush_candles(self, key: Optional[str] = None) -> None:
        """Write buffered candle data to Parquet files.

        Args:
            key: Specific buffer key to flush. If None, flushes all.
        """
        keys = [key] if key else list(self._candle_buffer.keys())
        for k in keys:
            buf = self._candle_buffer.get(k, [])
            if not buf:
                continue

            df = pd.DataFrame(buf)
            symbol = buf[0]["symbol"]
            timeframe = buf[0]["timeframe"]

            dir_path = self._data_dir / "candles" / symbol
            dir_path.mkdir(parents=True, exist_ok=True)

            # Group by date and write separate files
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df["date"] = df["datetime"].dt.strftime("%Y-%m-%d")

            for date, group in df.groupby("date"):
                file_path = dir_path / f"{date}_{timeframe}.parquet"
                self._append_to_parquet(file_path, group.drop(columns=["date"]))

            self._candle_buffer[k] = []
            logger.info("Flushed %d candles for %s", len(buf), k)

    def flush_ticks(self, symbol: Optional[str] = None) -> None:
        """Write buffered tick data to Parquet files."""
        symbols = [symbol] if symbol else list(self._tick_buffer.keys())
        for sym in symbols:
            buf = self._tick_buffer.get(sym, [])
            if not buf:
                continue

            df = pd.DataFrame(buf)
            dir_path = self._data_dir / "ticks" / sym
            dir_path.mkdir(parents=True, exist_ok=True)

            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df["date"] = df["datetime"].dt.strftime("%Y-%m-%d")

            for date, group in df.groupby("date"):
                file_path = dir_path / f"{date}.parquet"
                self._append_to_parquet(file_path, group.drop(columns=["date"]))

            self._tick_buffer[sym] = []
            logger.info("Flushed %d ticks for %s", len(buf), sym)

    def flush_all(self) -> None:
        """Flush all buffers."""
        self.flush_candles()
        self.flush_ticks()

    def load_candles(
        self,
        symbol: str,
        timeframe: str = "15m",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Load candle data from Parquet files.

        Args:
            symbol: Trading pair.
            timeframe: Candle timeframe.
            start_date: Start date string (YYYY-MM-DD), inclusive.
            end_date: End date string (YYYY-MM-DD), inclusive.

        Returns:
            DataFrame with OHLCV data sorted by timestamp.
        """
        dir_path = self._data_dir / "candles" / symbol
        if not dir_path.exists():
            return pd.DataFrame()

        pattern = f"*_{"15m" if timeframe == "15m" else timeframe}.parquet"
        files = sorted(dir_path.glob(pattern))

        if not files:
            return pd.DataFrame()

        dfs = []
        for f in files:
            # Filter by date range from filename
            date_str = f.stem.split("_")[0]
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            dfs.append(pd.read_parquet(f))

        if not dfs:
            return pd.DataFrame()

        result = pd.concat(dfs, ignore_index=True)
        result = result.sort_values("timestamp").reset_index(drop=True)
        return result

    @staticmethod
    def _append_to_parquet(file_path: Path, new_data: pd.DataFrame) -> None:
        """Append data to an existing Parquet file, or create a new one."""
        if file_path.exists():
            existing = pd.read_parquet(file_path)
            combined = pd.concat([existing, new_data], ignore_index=True)
            # Deduplicate by timestamp
            combined = combined.drop_duplicates(subset=["timestamp"], keep="last")
            combined.to_parquet(file_path, index=False)
        else:
            new_data.to_parquet(file_path, index=False)
