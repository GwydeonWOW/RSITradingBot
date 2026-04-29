"""Performance reporting routes."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.dependencies import get_db
from app.models.position import Position, PositionStatus
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/performance")
async def get_performance_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get aggregated performance summary from closed positions."""
    stmt = (
        select(
            func.count(Position.id).label("total_trades"),
            func.sum(Position.realized_pnl).label("total_pnl"),
            func.sum(
                case(
                    (Position.realized_pnl > 0, 1),
                    else_=0,
                )
            ).label("winners"),
            func.sum(
                case(
                    (Position.realized_pnl < 0, 1),
                    else_=0,
                )
            ).label("losers"),
            func.avg(Position.realized_pnl).label("avg_pnl"),
            func.max(Position.realized_pnl).label("best_trade"),
            func.min(Position.realized_pnl).label("worst_trade"),
        )
        .where(
            Position.user_id == current_user.id,
            Position.status == PositionStatus.CLOSED,
        )
    )

    result = await db.execute(stmt)
    row = result.one()

    total_trades = row.total_trades or 0
    if total_trades == 0:
        return {
            "total_trades": 0,
            "message": "No closed trades yet. Performance metrics will appear after trades are closed.",
        }

    total_pnl = float(row.total_pnl or 0)
    winners = row.winners or 0
    losers = row.losers or 0
    win_rate = winners / total_trades if total_trades > 0 else 0.0

    gross_profit = float(
        (await db.execute(
            select(func.sum(Position.realized_pnl)).where(
                Position.user_id == current_user.id,
                Position.status == PositionStatus.CLOSED,
                Position.realized_pnl > 0,
            )
        )).scalar() or 0
    )
    gross_loss = abs(float(
        (await db.execute(
            select(func.sum(Position.realized_pnl)).where(
                Position.user_id == current_user.id,
                Position.status == PositionStatus.CLOSED,
                Position.realized_pnl < 0,
            )
        )).scalar() or 0
    ))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    avg_pnl = float(row.avg_pnl or 0)

    return {
        "total_trades": total_trades,
        "winners": winners,
        "losers": losers,
        "win_rate": round(win_rate, 4),
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(avg_pnl, 2),
        "best_trade": round(float(row.best_trade or 0), 2),
        "worst_trade": round(float(row.worst_trade or 0), 2),
        "profit_factor": round(profit_factor, 4),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
    }


@router.get("/performance/{strategy_id}")
async def get_strategy_performance(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get performance metrics for a specific strategy."""
    import uuid
    try:
        uuid.UUID(strategy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid strategy ID format")

    stmt = (
        select(
            func.count(Position.id).label("total_trades"),
            func.sum(Position.realized_pnl).label("total_pnl"),
            func.avg(Position.realized_pnl).label("avg_pnl"),
            func.sum(
                case(
                    (Position.realized_pnl > 0, 1),
                    else_=0,
                )
            ).label("winners"),
        )
        .where(
            Position.user_id == current_user.id,
            Position.strategy_id == uuid.UUID(strategy_id),
            Position.status == PositionStatus.CLOSED,
        )
    )

    result = await db.execute(stmt)
    row = result.one()

    total_trades = row.total_trades or 0
    if total_trades == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy {strategy_id} has no closed trades.",
        )

    total_pnl = float(row.total_pnl or 0)
    winners = row.winners or 0
    win_rate = winners / total_trades if total_trades > 0 else 0.0

    return {
        "strategy_id": strategy_id,
        "total_trades": total_trades,
        "winners": winners,
        "win_rate": round(win_rate, 4),
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(float(row.avg_pnl or 0), 2),
    }
