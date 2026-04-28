"""Signal detection module.

Detects trade signals based on RSI pullback/bounce patterns within a
confirmed regime. The logic operates across two timeframes:

- 1H RSI for the signal condition (pullback to 40-48 in bullish regime,
  or bounce to 52-60 in bearish regime).
- 15M candle close for entry confirmation.

Signal lifecycle:
  1. Regime confirmed (4H RSI > 55 bullish or < 45 bearish).
  2. 1H RSI enters the pullback/bounce zone.
  3. 1H RSI reclaims (long) or loses (short) the trigger level.
  4. Confirmation on 15M candle close.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence

from app.core.regime import Regime, RegimeState


class SignalType(str, Enum):
    """Trade signal direction."""

    LONG = "long"
    SHORT = "short"
    NONE = "none"


class SignalStage(str, Enum):
    """Where the signal is in its lifecycle."""

    INACTIVE = "inactive"  # No setup detected
    SETUP = "setup"  # RSI entered pullback/bounce zone
    TRIGGER = "trigger"  # RSI reclaimed/lost the threshold
    CONFIRMED = "confirmed"  # 15M confirmation candle closed


@dataclass(frozen=True)
class Signal:
    """A trade signal with full context."""

    signal_type: SignalType
    stage: SignalStage
    regime: Regime
    rsi_1h: float
    rsi_4h: float
    price: float
    bar_index: int = -1
    strength: float = 0.0

    @property
    def is_actionable(self) -> bool:
        return self.stage == SignalStage.CONFIRMED and self.signal_type != SignalType.NONE


@dataclass
class SignalDetectorState:
    """Mutable state for the streaming signal detector.

    Tracks where we are in the signal lifecycle so the detector can
    process bars one at a time without look-ahead.
    """

    regime: Regime = Regime.NEUTRAL
    stage: SignalStage = SignalStage.INACTIVE
    signal_type: SignalType = SignalType.NONE
    rsi_at_setup: float = 0.0
    bars_in_setup: int = 0
    rsi_extreme_in_zone: float = 0.0  # best RSI reading inside the zone


class SignalDetector:
    """Streaming signal detector that processes bars chronologically.

    Usage:
        detector = SignalDetector()
        for bar in bars:
            signal = detector.on_bar(regime, rsi_1h, price, bar_index)
            if signal.is_actionable:
                # execute trade
    """

    def __init__(
        self,
        long_pullback_low: float = 40.0,
        long_pullback_high: float = 48.0,
        long_reclaim: float = 50.0,
        short_bounce_low: float = 52.0,
        short_bounce_high: float = 60.0,
        short_lose: float = 50.0,
        max_setup_bars: int = 48,  # max 1H bars to wait for trigger (~2 days)
    ) -> None:
        self._long_pullback_low = long_pullback_low
        self._long_pullback_high = long_pullback_high
        self._long_reclaim = long_reclaim
        self._short_bounce_low = short_bounce_low
        self._short_bounce_high = short_bounce_high
        self._short_lose = short_lose
        self._max_setup_bars = max_setup_bars
        self._state = SignalDetectorState()

    @property
    def state(self) -> SignalDetectorState:
        return self._state

    def reset(self) -> None:
        """Reset detector state, typically on regime change."""
        self._state = SignalDetectorState()

    def on_1h_bar(
        self,
        regime: Regime,
        rsi_1h: float,
        price: float,
        bar_index: int = -1,
        rsi_4h: float = 0.0,
    ) -> Signal:
        """Process a 1H bar and advance the signal lifecycle.

        This is the primary entry point. It checks if:
        1. A new setup forms (RSI enters pullback/bounce zone in the right regime).
        2. An existing setup triggers (RSI reclaims/loses the threshold).
        3. A setup expires (too many bars, regime change).

        Args:
            regime: Current regime from 4H timeframe.
            rsi_1h: RSI value on the 1H timeframe.
            price: Current close price.
            bar_index: Bar index for bookkeeping.
            rsi_4h: 4H RSI for signal context.

        Returns:
            Signal with current stage and type.
        """
        # Regime change invalidates any active setup
        if regime != self._state.regime and self._state.stage != SignalStage.INACTIVE:
            self.reset()

        self._state.regime = regime

        # Check for expiry
        if self._state.stage == SignalStage.SETUP:
            self._state.bars_in_setup += 1
            if self._state.bars_in_setup > self._max_setup_bars:
                self.reset()

        # No active setup: look for new setups
        if self._state.stage == SignalStage.INACTIVE:
            return self._check_for_setup(regime, rsi_1h, price, bar_index, rsi_4h)

        # Active setup: look for trigger
        if self._state.stage == SignalStage.SETUP:
            return self._check_for_trigger(rsi_1h, price, bar_index, rsi_4h)

        return Signal(
            signal_type=self._state.signal_type,
            stage=self._state.stage,
            regime=self._state.regime,
            rsi_1h=rsi_1h,
            rsi_4h=rsi_4h,
            price=price,
            bar_index=bar_index,
        )

    def confirm_on_15m_close(
        self,
        price: float,
        rsi_1h: float,
        rsi_4h: float,
        bar_index: int = -1,
        is_bullish_close: bool = True,
    ) -> Signal:
        """Confirm a trigger signal on 15M candle close.

        For longs: 15M candle should close bullish (close > open).
        For shorts: 15M candle should close bearish (close < open).

        Args:
            price: 15M candle close price.
            rsi_1h: Current 1H RSI.
            rsi_4h: Current 4H RSI.
            bar_index: Bar index.
            is_bullish_close: Whether the confirming candle is bullish.

        Returns:
            Signal with CONFIRMED stage if confirmation passes.
        """
        if self._state.stage != SignalStage.TRIGGER:
            return Signal(
                signal_type=self._state.signal_type,
                stage=self._state.stage,
                regime=self._state.regime,
                rsi_1h=rsi_1h,
                rsi_4h=rsi_4h,
                price=price,
                bar_index=bar_index,
            )

        # Confirmation criteria
        confirmed = False
        if self._state.signal_type == SignalType.LONG and is_bullish_close:
            confirmed = True
        elif self._state.signal_type == SignalType.SHORT and not is_bullish_close:
            confirmed = True

        if confirmed:
            strength = compute_signal_strength(
                self._state.signal_type,
                rsi_1h,
                self._state.rsi_extreme_in_zone,
                self._state.bars_in_setup,
            )
            signal = Signal(
                signal_type=self._state.signal_type,
                stage=SignalStage.CONFIRMED,
                regime=self._state.regime,
                rsi_1h=rsi_1h,
                rsi_4h=rsi_4h,
                price=price,
                bar_index=bar_index,
                strength=strength,
            )
            # Reset after confirmed signal
            self._state.stage = SignalStage.INACTIVE
            self._state.signal_type = SignalType.NONE
            return signal

        # Confirmation failed; keep trigger state for next 15M bar
        return Signal(
            signal_type=self._state.signal_type,
            stage=SignalStage.TRIGGER,
            regime=self._state.regime,
            rsi_1h=rsi_1h,
            rsi_4h=rsi_4h,
            price=price,
            bar_index=bar_index,
        )

    def _check_for_setup(
        self, regime: Regime, rsi_1h: float, price: float, bar_index: int, rsi_4h: float
    ) -> Signal:
        """Look for a new setup (RSI entering the pullback/bounce zone)."""
        # Long setup: bullish regime + RSI pulls back into 40-48 zone
        if regime == Regime.BULLISH and self._long_pullback_low <= rsi_1h <= self._long_pullback_high:
            self._state.stage = SignalStage.SETUP
            self._state.signal_type = SignalType.LONG
            self._state.rsi_at_setup = rsi_1h
            self._state.rsi_extreme_in_zone = rsi_1h
            self._state.bars_in_setup = 0
            return Signal(
                signal_type=SignalType.LONG,
                stage=SignalStage.SETUP,
                regime=regime,
                rsi_1h=rsi_1h,
                rsi_4h=rsi_4h,
                price=price,
                bar_index=bar_index,
            )

        # Short setup: bearish regime + RSI bounces into 52-60 zone
        if regime == Regime.BEARISH and self._short_bounce_low <= rsi_1h <= self._short_bounce_high:
            self._state.stage = SignalStage.SETUP
            self._state.signal_type = SignalType.SHORT
            self._state.rsi_at_setup = rsi_1h
            self._state.rsi_extreme_in_zone = rsi_1h
            self._state.bars_in_setup = 0
            return Signal(
                signal_type=SignalType.SHORT,
                stage=SignalStage.SETUP,
                regime=regime,
                rsi_1h=rsi_1h,
                rsi_4h=rsi_4h,
                price=price,
                bar_index=bar_index,
            )

        return Signal(
            signal_type=SignalType.NONE,
            stage=SignalStage.INACTIVE,
            regime=regime,
            rsi_1h=rsi_1h,
            rsi_4h=rsi_4h,
            price=price,
            bar_index=bar_index,
        )

    def _check_for_trigger(
        self, rsi_1h: float, price: float, bar_index: int, rsi_4h: float
    ) -> Signal:
        """Check if the active setup has triggered."""
        # Track the extreme RSI reading inside the zone
        if self._state.signal_type == SignalType.LONG:
            if rsi_1h < self._state.rsi_extreme_in_zone:
                self._state.rsi_extreme_in_zone = rsi_1h
            # Trigger: RSI reclaims the reclaim level
            if rsi_1h >= self._long_reclaim:
                self._state.stage = SignalStage.TRIGGER
                return Signal(
                    signal_type=SignalType.LONG,
                    stage=SignalStage.TRIGGER,
                    regime=self._state.regime,
                    rsi_1h=rsi_1h,
                    rsi_4h=rsi_4h,
                    price=price,
                    bar_index=bar_index,
                )

        elif self._state.signal_type == SignalType.SHORT:
            if rsi_1h > self._state.rsi_extreme_in_zone:
                self._state.rsi_extreme_in_zone = rsi_1h
            # Trigger: RSI loses the threshold
            if rsi_1h <= self._short_lose:
                self._state.stage = SignalStage.TRIGGER
                return Signal(
                    signal_type=SignalType.SHORT,
                    stage=SignalStage.TRIGGER,
                    regime=self._state.regime,
                    rsi_1h=rsi_1h,
                    rsi_4h=rsi_4h,
                    price=price,
                    bar_index=bar_index,
                )

        # Still in setup, RSI hasn't triggered yet
        return Signal(
            signal_type=self._state.signal_type,
            stage=SignalStage.SETUP,
            regime=self._state.regime,
            rsi_1h=rsi_1h,
            rsi_4h=rsi_4h,
            price=price,
            bar_index=bar_index,
        )


def compute_signal_strength(
    signal_type: SignalType,
    rsi_1h: float,
    rsi_extreme: float,
    bars_in_setup: int,
) -> float:
    """Compute a 0-1 strength score for a confirmed signal.

    Stronger signals have:
    - Deeper pullback (long) / higher bounce (short) before trigger.
    - Faster trigger (fewer bars in setup).

    Returns:
        Float in [0, 1] where 1.0 is strongest.
    """
    # Depth component: how deep into the zone did RSI go
    if signal_type == SignalType.LONG:
        # Long: lower extreme = deeper pullback = stronger
        # Zone is 40-48, so extreme going to 40 is best
        depth = max(0.0, min(1.0, (48.0 - rsi_extreme) / 8.0))
    else:
        # Short: higher extreme = higher bounce = stronger
        # Zone is 52-60, so extreme going to 60 is best
        depth = max(0.0, min(1.0, (rsi_extreme - 52.0) / 8.0))

    # Speed component: fewer bars = faster trigger = stronger
    # Normalized: 0 bars = 1.0, max_bars = 0.0
    speed = max(0.0, 1.0 - (bars_in_setup / 48.0))

    # Weighted combination: depth is more important
    strength = 0.6 * depth + 0.4 * speed
    return round(max(0.0, min(1.0, strength)), 4)
