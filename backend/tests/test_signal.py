"""Unit tests for signal detection."""

import pytest

from app.core.signal import (
    Signal,
    SignalDetector,
    SignalStage,
    SignalType,
    compute_signal_strength,
)
from app.core.regime import Regime


class TestSignalDetector:
    """Tests for the streaming signal detector."""

    def test_no_signal_in_neutral_regime(self):
        """No signals should fire in neutral regime."""
        detector = SignalDetector()
        signal = detector.on_1h_bar(
            regime=Regime.NEUTRAL,
            rsi_1h=44.0,
            price=50000.0,
            rsi_4h=50.0,
        )
        assert signal.signal_type == SignalType.NONE
        assert signal.stage == SignalStage.INACTIVE

    def test_long_setup_in_bullish_regime(self):
        """RSI pulling back to 40-48 in bullish regime creates a long setup."""
        detector = SignalDetector()
        signal = detector.on_1h_bar(
            regime=Regime.BULLISH,
            rsi_1h=44.0,
            price=50000.0,
            rsi_4h=58.0,
        )
        assert signal.signal_type == SignalType.LONG
        assert signal.stage == SignalStage.SETUP

    def test_short_setup_in_bearish_regime(self):
        """RSI bouncing to 52-60 in bearish regime creates a short setup."""
        detector = SignalDetector()
        signal = detector.on_1h_bar(
            regime=Regime.BEARISH,
            rsi_1h=56.0,
            price=50000.0,
            rsi_4h=40.0,
        )
        assert signal.signal_type == SignalType.SHORT
        assert signal.stage == SignalStage.SETUP

    def test_long_trigger_after_setup(self):
        """After setup, RSI reclaiming 50 triggers the signal."""
        detector = SignalDetector()

        # Create setup
        detector.on_1h_bar(
            regime=Regime.BULLISH,
            rsi_1h=44.0,
            price=50000.0,
            rsi_4h=58.0,
        )

        # Trigger: RSI reclaims 50
        signal = detector.on_1h_bar(
            regime=Regime.BULLISH,
            rsi_1h=51.0,
            price=50500.0,
            rsi_4h=58.0,
        )
        assert signal.signal_type == SignalType.LONG
        assert signal.stage == SignalStage.TRIGGER

    def test_short_trigger_after_setup(self):
        """After short setup, RSI losing 50 triggers the signal."""
        detector = SignalDetector()

        # Create setup
        detector.on_1h_bar(
            regime=Regime.BEARISH,
            rsi_1h=56.0,
            price=50000.0,
            rsi_4h=40.0,
        )

        # Trigger: RSI loses 50
        signal = detector.on_1h_bar(
            regime=Regime.BEARISH,
            rsi_1h=49.0,
            price=49500.0,
            rsi_4h=40.0,
        )
        assert signal.signal_type == SignalType.SHORT
        assert signal.stage == SignalStage.TRIGGER

    def test_15m_confirmation_long(self):
        """15M bullish close confirms a long signal."""
        detector = SignalDetector()

        # Setup and trigger
        detector.on_1h_bar(regime=Regime.BULLISH, rsi_1h=44.0, price=50000.0, rsi_4h=58.0)
        detector.on_1h_bar(regime=Regime.BULLISH, rsi_1h=51.0, price=50500.0, rsi_4h=58.0)

        # Confirm on 15M
        confirmed = detector.confirm_on_15m_close(
            price=50600.0, rsi_1h=51.0, rsi_4h=58.0, is_bullish_close=True,
        )
        assert confirmed.signal_type == SignalType.LONG
        assert confirmed.stage == SignalStage.CONFIRMED
        assert confirmed.is_actionable

    def test_15m_rejection_long(self):
        """15M bearish close does NOT confirm a long signal."""
        detector = SignalDetector()

        detector.on_1h_bar(regime=Regime.BULLISH, rsi_1h=44.0, price=50000.0, rsi_4h=58.0)
        detector.on_1h_bar(regime=Regime.BULLISH, rsi_1h=51.0, price=50500.0, rsi_4h=58.0)

        rejected = detector.confirm_on_15m_close(
            price=50400.0, rsi_1h=51.0, rsi_4h=58.0, is_bullish_close=False,
        )
        assert rejected.stage == SignalStage.TRIGGER
        assert not rejected.is_actionable

    def test_15m_confirmation_short(self):
        """15M bearish close confirms a short signal."""
        detector = SignalDetector()

        detector.on_1h_bar(regime=Regime.BEARISH, rsi_1h=56.0, price=50000.0, rsi_4h=40.0)
        detector.on_1h_bar(regime=Regime.BEARISH, rsi_1h=49.0, price=49500.0, rsi_4h=40.0)

        confirmed = detector.confirm_on_15m_close(
            price=49400.0, rsi_1h=49.0, rsi_4h=40.0, is_bullish_close=False,
        )
        assert confirmed.signal_type == SignalType.SHORT
        assert confirmed.stage == SignalStage.CONFIRMED

    def test_regime_change_resets(self):
        """Changing regime resets the detector state."""
        detector = SignalDetector()

        # Create long setup in bullish
        detector.on_1h_bar(regime=Regime.BULLISH, rsi_1h=44.0, price=50000.0, rsi_4h=58.0)
        assert detector.state.stage == SignalStage.SETUP

        # Switch to bearish regime
        signal = detector.on_1h_bar(regime=Regime.BEARISH, rsi_1h=56.0, price=49000.0, rsi_4h=42.0)
        # Should be a new short setup, not carryover from long
        assert signal.signal_type == SignalType.SHORT

    def test_rsi_outside_pullback_zone_no_setup(self):
        """RSI outside the pullback zone should not create a setup."""
        detector = SignalDetector()
        signal = detector.on_1h_bar(
            regime=Regime.BULLISH,
            rsi_1h=55.0,  # above 48
            price=50000.0,
            rsi_4h=58.0,
        )
        assert signal.signal_type == SignalType.NONE

    def test_rsi_outside_bounce_zone_no_setup(self):
        """RSI outside the bounce zone should not create a short setup."""
        detector = SignalDetector()
        signal = detector.on_1h_bar(
            regime=Regime.BEARISH,
            rsi_1h=48.0,  # below 52
            price=50000.0,
            rsi_4h=40.0,
        )
        assert signal.signal_type == SignalType.NONE


class TestComputeSignalStrength:
    """Tests for signal strength calculation."""

    def test_strong_long_signal(self):
        """Deep pullback with fast trigger should be strong."""
        strength = compute_signal_strength(
            signal_type=SignalType.LONG,
            rsi_1h=52.0,
            rsi_extreme=40.0,  # deepest possible pullback
            bars_in_setup=2,
        )
        assert strength > 0.8

    def test_weak_long_signal(self):
        """Shallow pullback with slow trigger should be weak."""
        strength = compute_signal_strength(
            signal_type=SignalType.LONG,
            rsi_1h=51.0,
            rsi_extreme=47.0,  # barely entered zone
            bars_in_setup=40,
        )
        assert strength < 0.3

    def test_strong_short_signal(self):
        """High bounce with fast trigger should be strong."""
        strength = compute_signal_strength(
            signal_type=SignalType.SHORT,
            rsi_1h=48.0,
            rsi_extreme=60.0,  # highest possible bounce
            bars_in_setup=3,
        )
        assert strength > 0.8

    def test_strength_bounded(self):
        """Signal strength should always be in [0, 1]."""
        for bars in [0, 10, 30, 48]:
            for extreme in [40, 44, 48]:
                strength = compute_signal_strength(
                    SignalType.LONG, 50.0, extreme, bars,
                )
                assert 0.0 <= strength <= 1.0
