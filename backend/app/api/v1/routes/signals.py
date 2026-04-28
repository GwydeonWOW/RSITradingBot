"""Signal evaluation routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter()


class SignalEvaluateRequest(BaseModel):
    """Request body for signal evaluation."""

    symbol: str
    closes_4h: List[float]
    closes_1h: List[float]
    price_15m: float
    is_bullish_15m: bool = True


class SignalEvaluateResponse(BaseModel):
    """Signal evaluation result."""

    regime: Optional[str] = None
    rsi_4h: Optional[float] = None
    rsi_1h: Optional[float] = None
    signal: Optional[Dict[str, Any]] = None
    sizing: Optional[Dict[str, Any]] = None


@router.post("/evaluate")
async def evaluate_signal(
    request: SignalEvaluateRequest,
    current_user: User = Depends(get_current_user),
) -> SignalEvaluateResponse:
    """Evaluate the RSI strategy for a given set of price data.

    Takes 4H, 1H closes and the current 15M price, runs through
    regime detection and signal generation.
    """
    from app.services.strategy_service import StrategyService

    service = StrategyService(
        equity=10000.0,
        current_exposure=0.0,
    )

    result = service.evaluate(
        closes_4h=request.closes_4h,
        closes_1h=request.closes_1h,
        price_15m=request.price_15m,
        is_bullish_15m=request.is_bullish_15m,
    )

    return SignalEvaluateResponse(**result)
