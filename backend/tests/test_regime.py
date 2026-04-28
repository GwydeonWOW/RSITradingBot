"""Unit tests for regime detection."""

import pytest

from app.core.regime import (
    Regime,
    RegimeTransition,
    compute_ema,
    compute_regime_series,
    detect_regime,
    detect_regime_transitions,
)


class TestDetectRegime:
    """Tests for single-point regime detection."""

    def test_bullish(self):
        assert detect_regime(60.0) == Regime.BULLISH

    def test_bullish_at_threshold(self):
        assert detect_regime(55.0) == Regime.BULLISH

    def test_bearish(self):
        assert detect_regime(35.0) == Regime.BEARISH

    def test_bearish_at_threshold(self):
        assert detect_regime(45.0) == Regime.BEARISH

    def test_neutral(self):
        assert detect_regime(50.0) == Regime.NEUTRAL

    def test_neutral_near_bullish(self):
        assert detect_regime(54.9) == Regime.NEUTRAL

    def test_neutral_near_bearish(self):
        assert detect_regime(45.1) == Regime.NEUTRAL

    def test_custom_thresholds(self):
        assert detect_regime(52.0, bullish_threshold=50.0) == Regime.BULLISH
        assert detect_regime(48.0, bearish_threshold=50.0) == Regime.BEARISH


class TestComputeRegimeSeries:
    """Tests for regime series computation."""

    def test_series_length(self, btc_closes):
        series = compute_regime_series(btc_closes)
        assert len(series) == len(btc_closes)

    def test_warmup_is_none(self, btc_closes):
        series = compute_regime_series(btc_closes, rsi_period=14)
        for i in range(14):
            assert series[i] is None

    def test_valid_entries_are_regimes(self, btc_closes):
        series = compute_regime_series(btc_closes)
        for regime in series[14:]:
            assert regime is not None
            assert isinstance(regime, Regime)


class TestDetectRegimeTransitions:
    """Tests for regime transition detection."""

    def test_no_transitions_when_stable(self):
        series = [None, None, Regime.BULLISH, Regime.BULLISH, Regime.BULLISH]
        transitions = detect_regime_transitions(series)
        assert len(transitions) == 0

    def test_detects_single_transition(self):
        series = [None, Regime.BULLISH, Regime.BULLISH, Regime.NEUTRAL]
        transitions = detect_regime_transitions(series)
        assert len(transitions) == 1
        assert transitions[0].from_regime == Regime.BULLISH
        assert transitions[0].to_regime == Regime.NEUTRAL

    def test_detects_multiple_transitions(self):
        series = [Regime.BULLISH, Regime.BULLISH, Regime.NEUTRAL, Regime.BEARISH]
        transitions = detect_regime_transitions(series)
        assert len(transitions) == 2

    def test_none_breaks_chain(self):
        series = [Regime.BULLISH, None, Regime.BULLISH]
        transitions = detect_regime_transitions(series)
        # None resets the chain, so BULLISH after None is not a transition
        assert len(transitions) == 0


class TestComputeEMA:
    """Tests for EMA calculation."""

    def test_insufficient_data(self):
        result = compute_ema([1.0, 2.0], period=5)
        assert all(v is None for v in result)

    def test_length_matches_input(self):
        values = [float(i) for i in range(20)]
        result = compute_ema(values, period=10)
        assert len(result) == len(values)

    def test_warmup_period(self):
        values = [float(i) for i in range(20)]
        result = compute_ema(values, period=10)
        # First period-1 values should be None
        for i in range(9):
            assert result[i] is None

    def test_first_ema_is_sma(self):
        """First EMA value should be the SMA of the first `period` values."""
        values = [float(i + 1) for i in range(20)]  # 1, 2, ..., 20
        result = compute_ema(values, period=5)
        expected_sma = sum(values[:5]) / 5  # = 3.0
        assert result[4] is not None
        assert abs(result[4] - expected_sma) < 1e-10

    def test_ema_follows_trend(self):
        """EMA should generally follow the trend of the data."""
        values = [10.0] * 10 + [20.0] * 10
        result = compute_ema(values, period=5)
        # EMA should approach 20 as we process more 20s
        last_ema = result[-1]
        assert last_ema is not None
        assert last_ema > 15.0  # should be converging toward 20
