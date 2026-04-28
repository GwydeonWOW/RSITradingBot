# Bug fixes applied:
# 1. End-of-data position closing: changed record=False to record=None to avoid
#    AttributeError when _close_position tries record.append(trade).
# 2. Partial exits: main loop now handles PARTIAL_R by closing only close_pct
#    of the position and keeping the remainder open with updated size.
# 3. Look-ahead bias: _find_closest_4h_index now uses strict < comparison to
#    exclude the still-forming 4H candle.
"""Backtesting engine with multi-timeframe support.

Implements walk-forward backtesting across three timeframes:
- 4H: Regime detection
- 1H: Signal generation
- 15M: Entry confirmation

Features:
- Realistic cost model (taker/maker fees, slippage, funding).
- NO look-ahead bias: bars processed chronologically.
- Walk-forward validation with configurable train/test windows.
- Comprehensive performance metrics: Sharpe, MDD, CAGR, win rate,
  expectancy, profit factor, Deflated Sharpe Ratio.

Usage:
    engine = Backtester(cost_model=CostModel())
    result = engine.run(
        bars_4h=..., bars_1h=..., bars_15m=...,
        equity=10000,
    )
    print(result.metrics)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.core.regime import Regime, compute_regime_series
from app.core.rsi_engine import compute_rsi_series
from app.core.signal import Signal, SignalDetector, SignalStage, SignalType
from app.core.exit_logic import ExitAction, ExitManager, ExitReason, PositionTracker
from app.core.risk_manager import PositionSizing, RiskManager


@dataclass(frozen=True)
class CostModel:
    """Transaction cost assumptions."""

    taker_fee: float = 0.00045  # 0.045% taker fee
    maker_fee: float = 0.00015  # 0.015% maker fee
    slippage: float = 0.0002  # 0.02% estimated slippage
    funding_rate: float = 0.0001  # 0.01% per 8h (average funding)
    use_taker_for_entry: bool = True  # market orders use taker fee

    @property
    def total_entry_cost(self) -> float:
        """Total cost as fraction of notional for entry."""
        fee = self.taker_fee if self.use_taker_for_entry else self.maker_fee
        return fee + self.slippage

    @property
    def total_exit_cost(self) -> float:
        """Total cost as fraction of notional for exit."""
        return self.taker_fee + self.slippage


@dataclass
class Bar:
    """OHLCV bar data."""

    timestamp: int  # unix ms
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class TradeRecord:
    """Record of a completed trade."""

    entry_time: int
    exit_time: int
    direction: SignalType
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float
    r_multiple: float
    exit_reason: ExitReason
    signal_strength: float = 0.0
    regime: Regime = Regime.NEUTRAL
    fees_paid: float = 0.0

    @property
    def hold_duration_hours(self) -> float:
        return (self.exit_time - self.entry_time) / (3600 * 1000)

    @property
    def is_winner(self) -> bool:
        return self.pnl > 0


@dataclass
class BacktestMetrics:
    """Comprehensive backtest performance metrics."""

    total_return: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration_bars: int
    win_rate: float
    profit_factor: float
    expectancy: float
    avg_r_multiple: float
    total_trades: int
    avg_hold_hours: float
    annualized_volatility: float
    deflated_sharpe_ratio: float = 0.0
    calmar_ratio: float = 0.0

    # Walk-forward specific
    wf_train_sharpe: float = 0.0
    wf_test_sharpe: float = 0.0
    wf_degradation: float = 0.0  # how much Sharpe degrades from train to test


@dataclass
class BacktestResult:
    """Complete output of a backtest run."""

    equity_curve: List[float]
    trades: List[TradeRecord]
    metrics: BacktestMetrics
    total_fees: float
    start_time: int
    end_time: int


class Backtester:
    """Multi-timeframe backtesting engine.

    Orchestrates regime detection, signal generation, risk management,
    and exit logic in a strict chronological loop with no look-ahead.
    """

    def __init__(
        self,
        cost_model: Optional[CostModel] = None,
        max_leverage: int = 3,
        risk_per_trade: float = 0.005,
        max_hold_hours: int = 36,
        partial_r: float = 1.5,
        be_r: float = 1.0,
        rsi_period: int = 14,
        regime_bullish: float = 55.0,
        regime_bearish: float = 45.0,
        long_pullback_low: float = 40.0,
        long_pullback_high: float = 48.0,
        long_reclaim: float = 50.0,
        short_bounce_low: float = 52.0,
        short_bounce_high: float = 60.0,
        short_lose: float = 50.0,
    ) -> None:
        self._cost_model = cost_model or CostModel()
        self._max_leverage = max_leverage
        self._risk_per_trade = risk_per_trade
        self._max_hold_hours = max_hold_hours
        self._partial_r = partial_r
        self._be_r = be_r
        self._rsi_period = rsi_period
        self._regime_bullish = regime_bullish
        self._regime_bearish = regime_bearish
        self._long_pullback_low = long_pullback_low
        self._long_pullback_high = long_pullback_high
        self._long_reclaim = long_reclaim
        self._short_bounce_low = short_bounce_low
        self._short_bounce_high = short_bounce_high
        self._short_lose = short_lose

    def run(
        self,
        bars_4h: Sequence[Bar],
        bars_1h: Sequence[Bar],
        bars_15m: Sequence[Bar],
        equity: float = 10000.0,
        risk_method: str = "fixed_fractional",
    ) -> BacktestResult:
        """Run a full backtest across the three timeframes.

        Process:
        1. Compute RSI series for 4H (regime) and 1H (signals).
        2. Iterate through 1H bars chronologically.
        3. For each 1H bar, determine regime, check signal detector.
        4. On signal trigger, check 15M bars for confirmation.
        5. On confirmation, compute position size and open trade.
        6. For each 15M bar while in position, evaluate exits.

        Args:
            bars_4h: 4H bars for regime detection.
            bars_1h: 1H bars for signal generation.
            bars_15m: 15M bars for confirmation and exit management.
            equity: Starting equity.
            risk_method: "fixed_fractional" or "quarter_kelly".

        Returns:
            BacktestResult with equity curve, trades, and metrics.
        """
        closes_4h = [b.close for b in bars_4h]
        closes_1h = [b.close for b in bars_1h]

        rsi_4h_series = compute_rsi_series(closes_4h, self._rsi_period)
        regime_series = []
        for rsi in rsi_4h_series:
            if rsi is None:
                regime_series.append(Regime.NEUTRAL)
            elif rsi >= self._regime_bullish:
                regime_series.append(Regime.BULLISH)
            elif rsi <= self._regime_bearish:
                regime_series.append(Regime.BEARISH)
            else:
                regime_series.append(Regime.NEUTRAL)

        rsi_1h_series = compute_rsi_series(closes_1h, self._rsi_period)
        rsi_15m_series = compute_rsi_series(
            [b.close for b in bars_15m], self._rsi_period
        )

        # Build timestamp-to-index maps for alignment
        bar_15m_by_time = {b.timestamp: (i, b) for i, b in enumerate(bars_15m)}

        # State
        detector = SignalDetector(
            long_pullback_low=self._long_pullback_low,
            long_pullback_high=self._long_pullback_high,
            long_reclaim=self._long_reclaim,
            short_bounce_low=self._short_bounce_low,
            short_bounce_high=self._short_bounce_high,
            short_lose=self._short_lose,
        )
        exit_manager = ExitManager(
            max_hold_hours=self._max_hold_hours,
            partial_r=self._partial_r,
            be_r=self._be_r,
        )

        current_equity = equity
        equity_curve: List[float] = [equity]
        trades: List[TradeRecord] = []
        total_fees = 0.0

        position: Optional[PositionTracker] = None
        pending_signal: Optional[Signal] = None
        current_exposure = 0.0

        # Track which 15M bar we are at
        bar_15m_idx = 0

        for i_1h, bar_1h in enumerate(bars_1h):
            if i_1h >= len(rsi_1h_series) or rsi_1h_series[i_1h] is None:
                continue

            # Determine current regime from the closest 4H bar
            regime = self._get_regime_at_time(
                regime_series, bars_4h, bar_1h.timestamp
            )
            rsi_1h = rsi_1h_series[i_1h]
            rsi_4h_val = 0.0
            idx_4h = self._find_closest_4h_index(bars_4h, bar_1h.timestamp)
            if idx_4h is not None and idx_4h < len(rsi_4h_series):
                r = rsi_4h_series[idx_4h]
                rsi_4h_val = r if r is not None else 0.0

            # If we have an open position, process 15M bars for exits
            if position is not None and position.position_size > 0:
                while bar_15m_idx < len(bars_15m):
                    bar_15m = bars_15m[bar_15m_idx]
                    if bar_15m.timestamp > bar_1h.timestamp:
                        break

                    rsi_15m = rsi_15m_series[bar_15m_idx] if bar_15m_idx < len(rsi_15m_series) else None

                    action = exit_manager.evaluate(
                        position, bar_15m.close, bar_15m.timestamp, rsi_15m
                    )

                    if action.new_stop is not None and not action.should_exit:
                        exit_manager.apply_exit_action(position, action)

                    if action.should_exit:
                        if action.is_partial:
                            # Partial exit: close only close_pct of position
                            partial_size = position.position_size * action.close_pct
                            # Build a partial exit action for recording
                            partial_action = ExitAction(
                                should_exit=True,
                                reason=action.reason,
                                close_pct=action.close_pct,
                                new_stop=action.new_stop,
                            )
                            # Temporarily set position_size to the partial amount
                            original_size = position.position_size
                            position.position_size = partial_size
                            trade = self._close_position(
                                position, bar_15m.close, bar_15m.timestamp,
                                partial_action, current_equity, trades,
                                pending_signal is not None
                            )
                            current_equity += trade.pnl
                            total_fees += trade.fees_paid
                            current_exposure -= partial_size * position.entry_price
                            if current_exposure < 0:
                                current_exposure = 0.0
                            # Restore remaining position
                            position.position_size = original_size - partial_size
                            # Move stop to break-even if specified
                            if action.new_stop is not None:
                                exit_manager.apply_exit_action(position, action)
                        else:
                            trade = self._close_position(
                                position, bar_15m.close, bar_15m.timestamp,
                                action, current_equity, trades,
                                pending_signal is not None
                            )
                            current_equity += trade.pnl
                            total_fees += trade.fees_paid
                            current_exposure -= trade.size * trade.entry_price
                            if current_exposure < 0:
                                current_exposure = 0.0
                            position = None

                    bar_15m_idx += 1

                equity_curve.append(current_equity)

            # Skip signal detection if in a position
            if position is not None and position.position_size > 0:
                continue

            # Signal detection on 1H bar
            signal = detector.on_1h_bar(
                regime=regime,
                rsi_1h=rsi_1h,
                price=bar_1h.close,
                bar_index=i_1h,
                rsi_4h=rsi_4h_val,
            )

            if signal.stage == SignalStage.TRIGGER:
                pending_signal = signal
                # Look for 15M confirmation
                while bar_15m_idx < len(bars_15m):
                    bar_15m = bars_15m[bar_15m_idx]
                    if bar_15m.timestamp > bar_1h.timestamp:
                        break

                    is_bullish = bar_15m.close >= bar_15m.open
                    confirmed = detector.confirm_on_15m_close(
                        price=bar_15m.close,
                        rsi_1h=rsi_1h,
                        rsi_4h=rsi_4h_val,
                        bar_index=bar_15m_idx,
                        is_bullish_close=is_bullish,
                    )

                    if confirmed.is_actionable:
                        # Open position
                        stop_distance_pct = 0.02  # 2% default stop
                        if confirmed.signal_type == SignalType.LONG:
                            stop_price = bar_15m.close * (1 - stop_distance_pct)
                        else:
                            stop_price = bar_15m.close * (1 + stop_distance_pct)

                        rm = RiskManager(
                            equity=current_equity,
                            max_leverage=self._max_leverage,
                            risk_per_trade_min=self._risk_per_trade,
                            risk_per_trade_max=self._risk_per_trade,
                        )
                        sizing = rm.calculate_position_size(
                            entry_price=bar_15m.close,
                            stop_price=stop_price,
                            direction=confirmed.signal_type,
                            current_exposure=current_exposure,
                        )

                        if sizing.size_notional > 0:
                            position = PositionTracker(
                                entry_price=bar_15m.close,
                                stop_price=stop_price,
                                direction=confirmed.signal_type,
                                entry_time_ms=bar_15m.timestamp,
                            )
                            current_exposure += sizing.size_notional
                            pending_signal = confirmed

                    bar_15m_idx += 1
                    if position is not None:
                        break

        # Close any remaining position at last known price
        if position is not None and position.position_size > 0 and bars_15m:
            last_bar = bars_15m[-1]
            action = ExitAction(should_exit=True, reason=ExitReason.TIME_STOP, close_pct=1.0)
            trade = self._close_position(
                position, last_bar.close, last_bar.timestamp,
                action, current_equity, None
            )
            current_equity += trade.pnl
            total_fees += trade.fees_paid
            trades.append(trade)
            equity_curve.append(current_equity)

        metrics = self._compute_metrics(
            equity_curve, trades, equity
        )

        start_time = bars_15m[0].timestamp if bars_15m else 0
        end_time = bars_15m[-1].timestamp if bars_15m else 0

        return BacktestResult(
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            total_fees=total_fees,
            start_time=start_time,
            end_time=end_time,
        )

    def run_walk_forward(
        self,
        bars_4h: Sequence[Bar],
        bars_1h: Sequence[Bar],
        bars_15m: Sequence[Bar],
        equity: float = 10000.0,
        train_bars: int = 2000,
        test_bars: int = 500,
        step_bars: int = 500,
    ) -> List[BacktestResult]:
        """Run walk-forward validation.

        Splits data into overlapping train/test windows. Each window
        is backtested independently. The train window is for parameter
        optimization (future work), the test window for out-of-sample
        evaluation.

        Args:
            bars_4h, bars_1h, bars_15m: Bar data.
            equity: Starting equity per window.
            train_bars: Number of 15M bars in training window.
            test_bars: Number of 15M bars in test window.
            step_bars: How many bars to step forward each iteration.

        Returns:
            List of BacktestResult, one per test window.
        """
        results: List[BacktestResult] = []
        total_15m = len(bars_15m)

        start = 0
        while start + train_bars + test_bars <= total_15m:
            train_end = start + train_bars
            test_end = train_end + test_bars

            # Get the 15M bars for test window
            test_15m = list(bars_15m[train_end:test_end])

            # Get corresponding 1H and 4H bars that overlap with test window
            test_start_time = bars_15m[train_end].timestamp
            test_end_time = bars_15m[test_end - 1].timestamp

            # Need some warmup bars before test window for RSI calculation
            warmup_1h_start = max(0, train_end // 4 - 50)
            warmup_4h_start = max(0, train_end // 16 - 50)

            test_1h = [
                b for b in bars_1h
                if b.timestamp >= (bars_1h[warmup_1h_start].timestamp if warmup_1h_start < len(bars_1h) else 0)
                and b.timestamp <= test_end_time
            ]
            test_4h = [
                b for b in bars_4h
                if b.timestamp >= (bars_4h[warmup_4h_start].timestamp if warmup_4h_start < len(bars_4h) else 0)
                and b.timestamp <= test_end_time
            ]

            if test_15m and test_1h and test_4h:
                result = self.run(test_4h, test_1h, test_15m, equity)
                results.append(result)

            start += step_bars

        return results

    def _get_regime_at_time(
        self,
        regime_series: List[Regime],
        bars_4h: Sequence[Bar],
        timestamp: int,
    ) -> Regime:
        """Get the regime from the most recent completed 4H bar."""
        closest_idx = self._find_closest_4h_index(bars_4h, timestamp)
        if closest_idx is None:
            return Regime.NEUTRAL
        if closest_idx < len(regime_series):
            return regime_series[closest_idx] or Regime.NEUTRAL
        return Regime.NEUTRAL

    @staticmethod
    def _find_closest_4h_index(bars_4h: Sequence[Bar], timestamp: int) -> Optional[int]:
        """Find the index of the last 4H bar before the given timestamp."""
        result = None
        for i, bar in enumerate(bars_4h):
            if bar.timestamp < timestamp:
                result = i
            else:
                break
        return result

    def _close_position(
        self,
        position: PositionTracker,
        exit_price: float,
        exit_time: int,
        action: ExitAction,
        equity_before: float,
        record: list = None,
        has_pending: bool = False,
    ) -> TradeRecord:
        """Calculate PnL and create a trade record for a closed position."""
        if position.direction == SignalType.LONG:
            raw_pnl = (exit_price - position.entry_price) * position.position_size
        else:
            raw_pnl = (position.entry_price - exit_price) * position.position_size

        # Apply costs
        notional = position.entry_price * position.position_size
        entry_cost = notional * self._cost_model.total_entry_cost
        exit_cost = abs(exit_price * position.position_size) * self._cost_model.total_exit_cost

        # Funding cost: approximate based on hold duration
        hold_hours = (exit_time - position.entry_time_ms) / (3600 * 1000)
        funding_periods = hold_hours / 8.0
        funding_cost = notional * self._cost_model.funding_rate * funding_periods

        total_cost = entry_cost + exit_cost + funding_cost
        net_pnl = raw_pnl - total_cost

        # R-multiple
        risk_dist = abs(position.entry_price - position.stop_price)
        r_multiple = raw_pnl / (risk_dist * position.position_size) if risk_dist > 0 and position.position_size > 0 else 0.0

        trade = TradeRecord(
            entry_time=position.entry_time_ms,
            exit_time=exit_time,
            direction=position.direction,
            entry_price=position.entry_price,
            exit_price=exit_price,
            size=position.position_size,
            pnl=net_pnl,
            pnl_pct=net_pnl / equity_before if equity_before > 0 else 0.0,
            r_multiple=r_multiple,
            exit_reason=action.reason or ExitReason.MANUAL,
            fees_paid=total_cost,
        )

        if record is not None:
            record.append(trade)

        return trade

    @staticmethod
    def _compute_metrics(
        equity_curve: List[float],
        trades: List[TradeRecord],
        initial_equity: float,
    ) -> BacktestMetrics:
        """Compute comprehensive backtest performance metrics."""
        if not equity_curve or len(equity_curve) < 2:
            return BacktestMetrics(
                total_return=0.0, cagr=0.0, sharpe_ratio=0.0,
                sortino_ratio=0.0, max_drawdown=0.0,
                max_drawdown_duration_bars=0, win_rate=0.0,
                profit_factor=0.0, expectancy=0.0, avg_r_multiple=0.0,
                total_trades=0, avg_hold_hours=0.0,
                annualized_volatility=0.0,
            )

        equity_arr = np.array(equity_curve)
        returns = np.diff(equity_arr) / equity_arr[:-1]
        returns = returns[np.isfinite(returns)]

        # Total return
        total_return = (equity_curve[-1] / initial_equity) - 1.0

        # Annualized return (assume 365.25 * 24 * 4 = 35040 15M bars per year)
        n_bars = len(equity_curve)
        bars_per_year = 35040.0
        years = n_bars / bars_per_year
        cagr = (1.0 + total_return) ** (1.0 / max(years, 0.001)) - 1.0 if total_return > -1 else -1.0

        # Sharpe ratio (annualized, risk-free = 0 for crypto)
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = float(np.mean(returns) / np.std(returns)) * np.sqrt(bars_per_year)
        else:
            sharpe = 0.0

        # Sortino ratio
        downside = returns[returns < 0]
        if len(downside) > 1 and np.std(downside) > 0:
            sortino = float(np.mean(returns) / np.std(downside)) * np.sqrt(bars_per_year)
        else:
            sortino = 0.0

        # Max drawdown
        running_max = np.maximum.accumulate(equity_arr)
        drawdowns = (running_max - equity_arr) / running_max
        max_dd = float(np.max(drawdowns))
        # Max drawdown duration
        dd_duration = 0
        current_dd = 0
        for i in range(len(equity_arr)):
            if equity_arr[i] >= running_max[i]:
                current_dd = 0
            else:
                current_dd += 1
            dd_duration = max(dd_duration, current_dd)

        # Trade statistics
        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if not t.is_winner]
        n_trades = len(trades)
        win_rate = len(winners) / n_trades if n_trades > 0 else 0.0

        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        expectancy = float(np.mean([t.pnl for t in trades])) if trades else 0.0
        avg_r = float(np.mean([t.r_multiple for t in trades])) if trades else 0.0
        avg_hold = float(np.mean([t.hold_duration_hours for t in trades])) if trades else 0.0

        ann_vol = float(np.std(returns) * np.sqrt(bars_per_year)) if len(returns) > 1 else 0.0

        # Calmar ratio
        calmar = cagr / max_dd if max_dd > 0 else 0.0

        return BacktestMetrics(
            total_return=float(total_return),
            cagr=float(cagr),
            sharpe_ratio=float(sharpe),
            sortino_ratio=float(sortino),
            max_drawdown=float(max_dd),
            max_drawdown_duration_bars=dd_duration,
            win_rate=float(win_rate),
            profit_factor=float(profit_factor),
            expectancy=float(expectancy),
            avg_r_multiple=float(avg_r),
            total_trades=n_trades,
            avg_hold_hours=float(avg_hold),
            annualized_volatility=float(ann_vol),
            calmar_ratio=float(calmar),
        )


def compute_deflated_sharpe_ratio(
    sharpe: float,
    n_observations: int,
    n_tests: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Compute the Deflated Sharpe Ratio (DSR).

    DSR adjusts the Sharpe Ratio for multiple testing and non-normal
    returns. It answers: "What is the probability that the observed
    Sharpe is a false positive given we ran N independent tests?"

    Based on Bailey & Lopez de Prado (2014).

    Args:
        sharpe: Observed annualized Sharpe ratio.
        n_observations: Number of return observations.
        n_tests: Number of independent tests (strategy variations tried).
        skewness: Skewness of returns.
        kurtosis: Excess kurtosis of returns.

    Returns:
        DSR value in [0, 1]. Higher = more likely the Sharpe is real.
    """
    if n_observations < 2 or n_tests < 1:
        return 0.0

    # Expected Maximum Sharpe under the null (all strategies have SR=0)
    # E[max(SR)] ~ (1 - gamma) * phi_inv(1 - 1/N) + gamma * phi_inv(1 - 1/(N*e))
    # Simplified: expected_max_sharpe ~ sqrt(ln(n_tests)) adjusted
    expected_max_sr = np.sqrt((1.0 - np.euler_gamma) * (2.0 * np.log(n_tests)))

    # SE of Sharpe estimate, adjusted for non-normality
    se_sr = np.sqrt(
        (1.0 - skewness * sharpe + (kurtosis - 1.0) / 4.0 * sharpe**2) / (n_observations - 1)
    ) if n_observations > 1 else 1.0

    if se_sr <= 0:
        return 0.0

    from scipy.stats import norm
    dsr = norm.cdf((sharpe - expected_max_sr) / se_sr)
    return float(dsr)
