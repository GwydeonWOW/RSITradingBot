"""CLI script for running backtests.

Usage:
    python scripts/run_backtest.py --symbol BTC --start 2024-01-01 --end 2024-12-31
    python scripts/run_backtest.py --symbol ETH --walk-forward
"""

import argparse
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.backtester import Backtester, Bar, CostModel
from app.services.backtest_service import BacktestService


def generate_synthetic_data(
    base_price: float,
    n_bars: int,
    volatility: float = 0.02,
    trend: float = 0.001,
    timeframe_ms: int = 900000,
    start_time: int = 1700000000000,
) -> list:
    """Generate synthetic price data for testing the backtester."""
    import random
    random.seed(42)

    bars = []
    price = base_price
    for i in range(n_bars):
        ret = random.gauss(trend, volatility)
        o = price
        c = price * (1 + ret)
        h = max(o, c) * (1 + abs(random.gauss(0, volatility * 0.3)))
        l = min(o, c) * (1 - abs(random.gauss(0, volatility * 0.3)))
        v = random.uniform(100, 10000)

        bars.append(Bar(
            timestamp=start_time + i * timeframe_ms,
            open=o, high=h, low=l, close=c, volume=v,
        ))
        price = c

    return bars


def main():
    parser = argparse.ArgumentParser(description="Run RSI strategy backtest")
    parser.add_argument("--symbol", default="BTC", help="Trading symbol")
    parser.add_argument("--start", default="2024-01-01", help="Start date")
    parser.add_argument("--end", default="2024-12-31", help="End date")
    parser.add_argument("--equity", type=float, default=10000.0, help="Starting equity")
    parser.add_argument("--walk-forward", action="store_true", help="Run walk-forward validation")
    parser.add_argument("--rsi-period", type=int, default=14, help="RSI period")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data")
    args = parser.parse_args()

    print(f"=== RSI Backtest: {args.symbol} ===")
    print(f"Period: {args.start} to {args.end}")
    print(f"Equity: ${args.equity:,.2f}")
    print(f"RSI Period: {args.rsi_period}")
    print()

    if args.synthetic:
        print("Using synthetic data for demonstration...")
        bars_15m = generate_synthetic_data(
            base_price=50000.0 if args.symbol == "BTC" else 3000.0,
            n_bars=8000,
            volatility=0.015,
            trend=0.0002,
            timeframe_ms=900000,
        )
        # Resample to 1H and 4H (just use subsets for simplicity)
        bars_1h = bars_15m[::4]
        bars_4h = bars_15m[::16]
    else:
        print("ERROR: Real data loading requires ClickHouse/Parquet setup.")
        print("Use --synthetic flag to test with generated data.")
        sys.exit(1)

    service = BacktestService()

    if args.walk_forward:
        print("Running walk-forward validation...")
        results = service.run_walk_forward(
            bars_4h=bars_4h,
            bars_1h=bars_1h,
            bars_15m=bars_15m,
            equity=args.equity,
            train_bars=2000,
            test_bars=500,
            step_bars=500,
        )
        print(f"\nWalk-forward: {len(results)} windows")
        for i, r in enumerate(results):
            m = r.metrics
            print(f"  Window {i + 1}: Trades={m.total_trades}, "
                  f"Sharpe={m.sharpe_ratio:.2f}, "
                  f"Return={m.total_return * 100:.1f}%, "
                  f"MDD={m.max_drawdown * 100:.1f}%")
    else:
        print("Running backtest...")
        result = service.run_backtest(
            bars_4h=bars_4h,
            bars_1h=bars_1h,
            bars_15m=bars_15m,
            equity=args.equity,
            params={"rsi_period": args.rsi_period},
        )

        m = result.metrics
        print(f"\n--- Results ---")
        print(f"Total Return:     {m.total_return * 100:.2f}%")
        print(f"CAGR:             {m.cagr * 100:.2f}%")
        print(f"Sharpe Ratio:     {m.sharpe_ratio:.3f}")
        print(f"Sortino Ratio:    {m.sortino_ratio:.3f}")
        print(f"Max Drawdown:     {m.max_drawdown * 100:.2f}%")
        print(f"Win Rate:         {m.win_rate * 100:.1f}%")
        print(f"Profit Factor:    {m.profit_factor:.2f}")
        print(f"Expectancy:       ${m.expectancy:.2f}")
        print(f"Avg R-Multiple:   {m.avg_r_multiple:.3f}")
        print(f"Total Trades:     {m.total_trades}")
        print(f"Avg Hold (hours): {m.avg_hold_hours:.1f}")
        print(f"Total Fees:       ${result.total_fees:.2f}")
        print(f"Calmar Ratio:     {m.calmar_ratio:.3f}")

        if m.total_trades > 0:
            winners = sum(1 for t in result.trades if t.is_winner)
            print(f"\nWinners: {winners}, Losers: {m.total_trades - winners}")


if __name__ == "__main__":
    main()
