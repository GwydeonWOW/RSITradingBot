"""Strategy routes: backtests, walk-forward, parameter management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.backtester import Bar
from app.data.recorder import MarketDataRecorder
from app.dependencies import get_db
from app.models.backtest import Backtest
from app.models.user import User
from app.services.backtest_service import BacktestService

router = APIRouter()
backtest_service = BacktestService()


class BacktestRequest(BaseModel):
    """Request body for running a backtest."""

    symbol: str = "BTC"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    equity: float = 10000.0
    params: Dict[str, Any] = Field(default_factory=lambda: {
        "rsi_period": 14,
        "regime_bullish": 55.0,
        "regime_bearish": 45.0,
        "risk_per_trade": 0.005,
        "max_leverage": 3,
    })


class WalkForwardRequest(BaseModel):
    """Request body for walk-forward validation."""

    symbol: str = "BTC"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    equity: float = 10000.0
    train_bars: int = 2000
    test_bars: int = 500
    step_bars: int = 500
    params: Dict[str, Any] = Field(default_factory=dict)


class BacktestResponse(BaseModel):
    """Response for a completed backtest."""

    result_id: str
    total_trades: int
    metrics: Dict[str, Any]


def _load_bars(symbol: str, timeframe: str, start_date: Optional[str], end_date: Optional[str]) -> List[Bar]:
    """Load candle data from Parquet and convert to Bar objects."""
    recorder = MarketDataRecorder()
    df = recorder.load_candles(symbol, timeframe, start_date, end_date)
    if df.empty:
        return []
    bars = []
    for row in df.itertuples():
        bars.append(Bar(
            timestamp=int(row.timestamp),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(getattr(row, "volume", 0) or 0),
        ))
    return bars


@router.post("/rsi/backtests")
async def run_backtest(
    request: BacktestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestResponse:
    """Run an RSI strategy backtest using stored market data."""
    bars_4h = _load_bars(request.symbol, "4h", request.start_date, request.end_date)
    bars_1h = _load_bars(request.symbol, "1h", request.start_date, request.end_date)
    bars_15m = _load_bars(request.symbol, "15m", request.start_date, request.end_date)

    if not bars_15m or not bars_1h or not bars_4h:
        raise HTTPException(
            status_code=422,
            detail=f"No market data available for {request.symbol}. "
                   "Ensure the data recorder has collected candles for this symbol.",
        )

    result = backtest_service.run_backtest(
        bars_4h=bars_4h,
        bars_1h=bars_1h,
        bars_15m=bars_15m,
        params=request.params,
        equity=request.equity,
    )

    result_id = f"bt_{len(backtest_service.list_results())}"

    bt_record = Backtest(
        user_id=current_user.id,
        name=f"RSI {request.symbol}",
        status="completed",
        parameters=request.params,
        universe=request.symbol,
        metrics={
            "total_return": result.metrics.total_return,
            "cagr": result.metrics.cagr,
            "sharpe_ratio": result.metrics.sharpe_ratio,
            "sortino_ratio": result.metrics.sortino_ratio,
            "max_drawdown": result.metrics.max_drawdown,
            "win_rate": result.metrics.win_rate,
            "profit_factor": result.metrics.profit_factor,
            "avg_r_multiple": result.metrics.avg_r_multiple,
            "total_trades": result.metrics.total_trades,
            "calmar_ratio": result.metrics.calmar_ratio,
        },
        trades_count=result.metrics.total_trades,
    )
    db.add(bt_record)
    await db.flush()

    return BacktestResponse(
        result_id=result_id,
        total_trades=result.metrics.total_trades,
        metrics={
            "total_return": result.metrics.total_return,
            "cagr": result.metrics.cagr,
            "sharpe_ratio": result.metrics.sharpe_ratio,
            "sortino_ratio": result.metrics.sortino_ratio,
            "max_drawdown": result.metrics.max_drawdown,
            "win_rate": result.metrics.win_rate,
            "profit_factor": result.metrics.profit_factor,
            "expectancy": result.metrics.expectancy,
            "avg_r_multiple": result.metrics.avg_r_multiple,
            "avg_hold_hours": result.metrics.avg_hold_hours,
            "total_trades": result.metrics.total_trades,
            "total_fees": result.total_fees,
            "calmar_ratio": result.metrics.calmar_ratio,
        },
    )


@router.post("/rsi/walkforward")
async def run_walk_forward(
    request: WalkForwardRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Run walk-forward validation on the RSI strategy."""
    bars_4h = _load_bars(request.symbol, "4h", request.start_date, request.end_date)
    bars_1h = _load_bars(request.symbol, "1h", request.start_date, request.end_date)
    bars_15m = _load_bars(request.symbol, "15m", request.start_date, request.end_date)

    if not bars_15m or not bars_1h or not bars_4h:
        raise HTTPException(
            status_code=422,
            detail=f"No market data available for {request.symbol}.",
        )

    results = backtest_service.run_walk_forward(
        bars_4h=bars_4h,
        bars_1h=bars_1h,
        bars_15m=bars_15m,
        params=request.params,
        equity=request.equity,
        train_bars=request.train_bars,
        test_bars=request.test_bars,
        step_bars=request.step_bars,
    )

    windows = []
    for i, r in enumerate(results):
        windows.append({
            "window": i + 1,
            "total_return": r.metrics.total_return,
            "sharpe_ratio": r.metrics.sharpe_ratio,
            "max_drawdown": r.metrics.max_drawdown,
            "win_rate": r.metrics.win_rate,
            "total_trades": r.metrics.total_trades,
        })

    avg_sharpe = sum(w["sharpe_ratio"] for w in windows) / len(windows) if windows else 0.0
    avg_return = sum(w["total_return"] for w in windows) / len(windows) if windows else 0.0

    return {
        "symbol": request.symbol,
        "total_windows": len(windows),
        "avg_sharpe": avg_sharpe,
        "avg_return": avg_return,
        "windows": windows,
    }


@router.get("/rsi/backtests/{result_id}")
async def get_backtest_result(
    result_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve a stored backtest result."""
    result = backtest_service.get_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Backtest result not found")

    return {
        "result_id": result_id,
        "metrics": {
            "total_return": result.metrics.total_return,
            "cagr": result.metrics.cagr,
            "sharpe_ratio": result.metrics.sharpe_ratio,
            "max_drawdown": result.metrics.max_drawdown,
            "win_rate": result.metrics.win_rate,
            "profit_factor": result.metrics.profit_factor,
            "total_trades": result.metrics.total_trades,
        },
        "total_fees": result.total_fees,
        "trade_count": len(result.trades),
    }


@router.get("/rsi/backtests")
async def list_backtests(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all stored backtest results."""
    return {
        "results": backtest_service.list_results(),
        "count": len(backtest_service.list_results()),
    }
