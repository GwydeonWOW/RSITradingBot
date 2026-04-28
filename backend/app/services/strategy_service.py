"""Strategy service.

Business logic for managing strategies, evaluating signals, and
coordinating the signal-to-order pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.regime import Regime, RegimeState, detect_regime
from app.core.rsi_engine import RSIResult, compute_rsi
from app.core.signal import Signal, SignalDetector, SignalType
from app.core.risk_manager import PositionSizing, RiskManager

logger = logging.getLogger(__name__)


class StrategyService:
    """Coordinates strategy evaluation and signal generation.

    Usage:
        service = StrategyService(
            risk_per_trade=0.005, max_leverage=3,
            equity=10000, current_exposure=0
        )
        decision = service.evaluate(
            closes_4h=[...], closes_1h=[...],
            price_15m=50000.0
        )
    """

    def __init__(
        self,
        risk_per_trade: float = 0.005,
        max_leverage: int = 3,
        equity: float = 10000.0,
        current_exposure: float = 0.0,
        rsi_period: int = 14,
        regime_bullish: float = 55.0,
        regime_bearish: float = 45.0,
    ) -> None:
        self._risk_per_trade = risk_per_trade
        self._max_leverage = max_leverage
        self._equity = equity
        self._current_exposure = current_exposure
        self._rsi_period = rsi_period
        self._regime_bullish = regime_bullish
        self._regime_bearish = regime_bearish
        self._detector = SignalDetector()

    def evaluate(
        self,
        closes_4h: List[float],
        closes_1h: List[float],
        price_15m: float,
        is_bullish_15m: bool = True,
    ) -> Dict[str, Any]:
        """Evaluate the strategy for a new data point.

        Runs through the full pipeline:
        1. Compute 4H RSI -> detect regime.
        2. Compute 1H RSI -> check signal detector.
        3. If trigger, check 15M confirmation.
        4. If confirmed, calculate position sizing.

        Returns:
            Dict with keys: regime, rsi_4h, rsi_1h, signal, sizing (if any).
        """
        result: Dict[str, Any] = {
            "regime": None,
            "rsi_4h": None,
            "rsi_1h": None,
            "signal": None,
            "sizing": None,
        }

        # Compute 4H RSI and regime
        rsi_4h_result = compute_rsi(closes_4h, self._rsi_period)
        if rsi_4h_result is None:
            return result

        result["rsi_4h"] = rsi_4h_result.rsi
        regime = detect_regime(
            rsi_4h_result.rsi, self._regime_bullish, self._regime_bearish
        )
        result["regime"] = regime.value

        # Compute 1H RSI
        rsi_1h_result = compute_rsi(closes_1h, self._rsi_period)
        if rsi_1h_result is None:
            return result

        result["rsi_1h"] = rsi_1h_result.rsi

        # Process through signal detector
        signal = self._detector.on_1h_bar(
            regime=regime,
            rsi_1h=rsi_1h_result.rsi,
            price=price_15m,
            rsi_4h=rsi_4h_result.rsi,
        )
        result["signal"] = {
            "type": signal.signal_type.value,
            "stage": signal.stage.value,
        }

        # If trigger, check 15M confirmation
        if signal.stage.value == "trigger":
            confirmed = self._detector.confirm_on_15m_close(
                price=price_15m,
                rsi_1h=rsi_1h_result.rsi,
                rsi_4h=rsi_4h_result.rsi,
                is_bullish_close=is_bullish_15m,
            )
            if confirmed.is_actionable:
                result["signal"] = {
                    "type": confirmed.signal_type.value,
                    "stage": confirmed.stage.value,
                    "strength": confirmed.strength,
                }

                # Calculate position sizing
                stop_distance_pct = 0.02
                if confirmed.signal_type == SignalType.LONG:
                    stop_price = price_15m * (1 - stop_distance_pct)
                else:
                    stop_price = price_15m * (1 + stop_distance_pct)

                rm = RiskManager(
                    equity=self._equity,
                    max_leverage=self._max_leverage,
                )
                sizing = rm.calculate_position_size(
                    entry_price=price_15m,
                    stop_price=stop_price,
                    direction=confirmed.signal_type,
                    current_exposure=self._current_exposure,
                )
                result["sizing"] = {
                    "notional": sizing.size_notional,
                    "contracts": sizing.size_contracts,
                    "leverage": sizing.leverage,
                    "risk_amount": sizing.risk_amount,
                }

        return result
