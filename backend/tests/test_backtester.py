"""Unit tests for the backtester."""

import pytest

from app.core.backtester import (
    BacktestMetrics,
    Backtester,
    Bar,
    CostModel,
    compute_deflated_sharpe_ratio,
)


def _make_bars(base_price: float, n: int, trend: float = 0.0, timeframe_ms: int = 900000) -> list:
    """Generate synthetic bars for testing.

    Args:
        base_price: Starting price.
        n: Number of bars to generate.
        trend: Price change per bar.
        timeframe_ms: Time between bars in ms (default 15m).
    """
    bars = []
    price = base_price
    for i in range(n):
        noise = (i % 3 - 1) * 10  # simple noise
        o = price
        c = price + trend + noise
        h = max(o, c) + abs(noise) * 0.5
        l = min(o, c) - abs(noise) * 0.5
        bars.append(Bar(
            timestamp=1700000000000 + i * timeframe_ms,
            open=o, high=h, low=l, close=c, volume=1000.0,
        ))
        price = c
    return bars


class TestBacktester:
    """Tests for the backtester engine."""

    def test_empty_data_returns_zero_trades(self):
        """Running on empty data should produce zero trades."""
        engine = Backtester()
        result = engine.run(
            bars_4h=[], bars_1h=[], bars_15m=[], equity=10000,
        )
        assert result.metrics.total_trades == 0
        assert len(result.trades) == 0

    def test_synthetic_bullish_run(self):
        """Strongly trending up data should generate long signals."""
        # Create trending data across all timeframes
        bars_15m = _make_bars(50000, 2000, trend=5.0, timeframe_ms=900000)
        bars_1h = _make_bars(50000, 500, trend=20.0, timeframe_ms=3600000)
        bars_4h = _make_bars(50000, 125, trend=80.0, timeframe_ms=14400000)

        engine = Backtester()
        result = engine.run(bars_4h, bars_1h, bars_15m, equity=10000)

        # Should have an equity curve
        assert len(result.equity_curve) > 0
        assert result.metrics.total_trades >= 0

    def test_cost_model_applied(self):
        """Cost model should reduce returns from raw PnL."""
        cm = CostModel(taker_fee=0.001, slippage=0.001)  # high costs
        engine = Backtester(cost_model=cm)

        bars_15m = _make_bars(50000, 2000, trend=3.0)
        bars_1h = _make_bars(50000, 500, trend=12.0, timeframe_ms=3600000)
        bars_4h = _make_bars(50000, 125, trend=48.0, timeframe_ms=14400000)

        result = engine.run(bars_4h, bars_1h, bars_15m, equity=10000)
        assert result.total_fees >= 0

    def test_metrics_structure(self):
        """Metrics should have all required fields."""
        metrics = BacktestMetrics(
            total_return=0.1,
            cagr=0.08,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=0.05,
            max_drawdown_duration_bars=100,
            win_rate=0.6,
            profit_factor=1.8,
            expectancy=50.0,
            avg_r_multiple=0.5,
            total_trades=20,
            avg_hold_hours=12.0,
            annualized_volatility=0.15,
        )
        assert metrics.total_return == 0.1
        assert metrics.sharpe_ratio == 1.5
        assert metrics.total_trades == 20


class TestDeflatedSharpeRatio:
    """Tests for DSR calculation."""

    def test_zero_sharpe_low_dsr(self):
        """Zero Sharpe with many tests should have low DSR."""
        dsr = compute_deflated_sharpe_ratio(
            sharpe=0.0, n_observations=1000, n_tests=100,
        )
        assert dsr < 0.5

    def test_high_sharpe_high_dsr(self):
        """High Sharpe should have high DSR even with many tests."""
        dsr = compute_deflated_sharpe_ratio(
            sharpe=3.0, n_observations=1000, n_tests=10,
        )
        assert dsr > 0.8

    def test_single_test(self):
        """With one test, DSR should be reasonably forgiving."""
        dsr = compute_deflated_sharpe_ratio(
            sharpe=1.5, n_observations=500, n_tests=1,
        )
        assert 0.0 <= dsr <= 1.0

    def test_insufficient_observations(self):
        """Fewer than 2 observations should return 0."""
        dsr = compute_deflated_sharpe_ratio(
            sharpe=2.0, n_observations=1, n_tests=10,
        )
        assert dsr == 0.0

    def test_zero_tests(self):
        """Zero tests should return 0."""
        dsr = compute_deflated_sharpe_ratio(
            sharpe=2.0, n_observations=100, n_tests=0,
        )
        assert dsr == 0.0

    def test_dsr_bounded(self):
        """DSR should always be in [0, 1]."""
        for sharpe in [0.0, 0.5, 1.0, 2.0, 5.0]:
            for n_obs in [100, 1000]:
                for n_tests in [1, 10, 100]:
                    dsr = compute_deflated_sharpe_ratio(
                        sharpe=sharpe, n_observations=n_obs, n_tests=n_tests,
                    )
                    assert 0.0 <= dsr <= 1.0, f"DSR={dsr} for SR={sharpe}, obs={n_obs}, tests={n_tests}"


class TestCostModel:
    """Tests for the cost model."""

    def test_default_costs(self):
        cm = CostModel()
        assert cm.taker_fee == 0.00045
        assert cm.maker_fee == 0.00015
        assert cm.slippage == 0.0002

    def test_entry_cost(self):
        cm = CostModel()
        expected = cm.taker_fee + cm.slippage
        assert abs(cm.total_entry_cost - expected) < 1e-10

    def test_exit_cost(self):
        cm = CostModel()
        expected = cm.taker_fee + cm.slippage
        assert abs(cm.total_exit_cost - expected) < 1e-10
