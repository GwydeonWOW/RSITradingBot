"""Backtest service.

Coordinates backtest execution, parameter management, and result storage.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.backtester import (
    BacktestMetrics,
    BacktestResult,
    Backtester,
    Bar,
    CostModel,
    compute_deflated_sharpe_ratio,
)

logger = logging.getLogger(__name__)


class BacktestService:
    """Service for running and managing backtests.

    Usage:
        service = BacktestService()
        result = service.run_backtest(
            bars_4h=..., bars_1h=..., bars_15m=...,
            params={"rsi_period": 14}
        )
        print(result.metrics)
    """

    def __init__(self) -> None:
        self._results: Dict[str, BacktestResult] = {}

    def run_backtest(
        self,
        bars_4h: List[Bar],
        bars_1h: List[Bar],
        bars_15m: List[Bar],
        params: Optional[Dict[str, Any]] = None,
        equity: float = 10000.0,
    ) -> BacktestResult:
        """Run a single backtest.

        Args:
            bars_4h: 4H bar data.
            bars_1h: 1H bar data.
            bars_15m: 15M bar data.
            params: Strategy parameter overrides.
            equity: Starting equity.

        Returns:
            BacktestResult with metrics and trade history.
        """
        params = params or {}

        engine = Backtester(
            cost_model=CostModel(
                taker_fee=params.get("taker_fee", 0.00045),
                maker_fee=params.get("maker_fee", 0.00015),
                slippage=params.get("slippage", 0.0002),
                funding_rate=params.get("funding_rate", 0.0001),
            ),
            max_leverage=params.get("max_leverage", 3),
            risk_per_trade=params.get("risk_per_trade", 0.005),
            max_hold_hours=params.get("max_hold_hours", 36),
            partial_r=params.get("partial_r", 1.5),
            be_r=params.get("be_r", 1.0),
            rsi_period=params.get("rsi_period", 14),
            regime_bullish=params.get("regime_bullish", 55.0),
            regime_bearish=params.get("regime_bearish", 45.0),
        )

        result = engine.run(bars_4h, bars_1h, bars_15m, equity)
        result_id = f"bt_{len(self._results) + 1}"
        self._results[result_id] = result

        logger.info(
            "Backtest %s complete: %d trades, Sharpe=%.2f, MDD=%.2f%%",
            result_id,
            result.metrics.total_trades,
            result.metrics.sharpe_ratio,
            result.metrics.max_drawdown * 100,
        )
        return result

    def run_walk_forward(
        self,
        bars_4h: List[Bar],
        bars_1h: List[Bar],
        bars_15m: List[Bar],
        params: Optional[Dict[str, Any]] = None,
        equity: float = 10000.0,
        train_bars: int = 2000,
        test_bars: int = 500,
        step_bars: int = 500,
    ) -> List[BacktestResult]:
        """Run walk-forward validation.

        Args:
            bars_4h, bars_1h, bars_15m: Bar data.
            params: Strategy parameter overrides.
            equity: Starting equity per window.
            train_bars: Number of 15M bars for training warmup.
            test_bars: Number of 15M bars for out-of-sample test.
            step_bars: Step size between windows.

        Returns:
            List of BacktestResult, one per test window.
        """
        params = params or {}

        engine = Backtester(
            cost_model=CostModel(),
            max_leverage=params.get("max_leverage", 3),
            risk_per_trade=params.get("risk_per_trade", 0.005),
            rsi_period=params.get("rsi_period", 14),
        )

        results = engine.run_walk_forward(
            bars_4h, bars_1h, bars_15m, equity,
            train_bars=train_bars,
            test_bars=test_bars,
            step_bars=step_bars,
        )

        for i, r in enumerate(results):
            self._results[f"wf_{i + 1}"] = r

        logger.info("Walk-forward complete: %d windows", len(results))
        return results

    def get_result(self, result_id: str) -> Optional[BacktestResult]:
        """Retrieve a stored backtest result."""
        return self._results.get(result_id)

    def list_results(self) -> List[str]:
        """List all stored result IDs."""
        return list(self._results.keys())

    @staticmethod
    def compute_dsr(
        sharpe: float,
        n_observations: int,
        n_independent_tests: int,
        returns: Optional[List[float]] = None,
    ) -> float:
        """Compute the Deflated Sharpe Ratio.

        Args:
            sharpe: Observed annualized Sharpe ratio.
            n_observations: Number of return observations.
            n_independent_tests: Number of independent strategy tests.
            returns: Return series for skewness/kurtosis calculation.

        Returns:
            DSR value in [0, 1].
        """
        import numpy as np

        skewness = 0.0
        kurtosis = 3.0

        if returns and len(returns) > 2:
            arr = np.array(returns)
            from scipy.stats import skew, kurtosis as kurt_func
            skewness = float(skew(arr))
            kurtosis = float(kurt_func(arr)) + 3.0  # convert excess to full

        return compute_deflated_sharpe_ratio(
            sharpe=sharpe,
            n_observations=n_observations,
            n_tests=n_independent_tests,
            skewness=skewness,
            kurtosis=kurtosis,
        )
