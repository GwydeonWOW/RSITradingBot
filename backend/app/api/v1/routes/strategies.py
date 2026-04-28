"""Strategy routes: backtests, walk-forward, parameter management."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
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


@router.post("/rsi/backtests")
async def run_backtest(
    request: BacktestRequest,
    current_user: User = Depends(get_current_user),
) -> BacktestResponse:
    """Run an RSI strategy backtest.

    Requires pre-loaded market data for the requested symbol and date range.
    """
    # In production, load data from ClickHouse/Parquet here
    raise HTTPException(
        status_code=501,
        detail="Backtest execution requires market data. Use the CLI script for now.",
    )


@router.post("/rsi/walkforward")
async def run_walk_forward(
    request: WalkForwardRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Run walk-forward validation on the RSI strategy."""
    raise HTTPException(
        status_code=501,
        detail="Walk-forward requires market data. Use the CLI script for now.",
    )


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
