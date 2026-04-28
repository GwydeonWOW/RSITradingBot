"""Performance reporting routes."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter()


class PerformanceReport(BaseModel):
    """Performance report summary."""

    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profit_factor: float
    avg_r_multiple: float
    period: str


@router.get("/performance")
async def get_performance_summary(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get aggregated performance summary across all tracked strategies.

    Returns key metrics including return, Sharpe, MDD, win rate.
    """
    # Placeholder: in production, aggregate from the database
    return {
        "message": "Performance reporting requires historical trade data.",
        "metrics_available": [
            "total_return", "cagr", "sharpe_ratio", "sortino_ratio",
            "max_drawdown", "win_rate", "profit_factor", "expectancy",
            "avg_r_multiple", "calmar_ratio", "deflated_sharpe_ratio",
        ],
    }


@router.get("/performance/{strategy_id}")
async def get_strategy_performance(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get performance metrics for a specific strategy."""
    raise HTTPException(
        status_code=404,
        detail=f"Strategy {strategy_id} not found or has no performance data.",
    )
