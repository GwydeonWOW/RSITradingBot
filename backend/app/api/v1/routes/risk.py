"""Risk management routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.risk_manager import RiskManager

router = APIRouter()


class PositionSizeRequest(BaseModel):
    """Request body for position sizing calculation."""

    equity: float = 10000.0
    entry_price: float
    stop_price: float
    direction: str  # "long" or "short"
    current_exposure: float = 0.0
    max_leverage: int = 3
    method: str = "fixed_fractional"  # or "quarter_kelly"
    win_rate: Optional[float] = None
    avg_win_loss_ratio: Optional[float] = None


class PositionSizeResponse(BaseModel):
    """Position sizing result."""

    size_notional: float
    size_contracts: float
    leverage: int
    risk_amount: float
    risk_pct: float
    margin_required: float


class VaRRequest(BaseModel):
    """Request body for VaR calculation."""

    returns: List[float]
    method: str = "historical"  # or "parametric"


class VaRResponse(BaseModel):
    """VaR calculation result."""

    var_95: float
    var_99: float
    cvar_95: float
    method: str


@router.post("/limits/position-size")
async def calculate_position_size(request: PositionSizeRequest) -> PositionSizeResponse:
    """Calculate position size based on risk parameters.

    Supports fixed fractional and quarter-Kelly sizing methods.
    """
    from app.core.signal import SignalType

    direction = SignalType.LONG if request.direction == "long" else SignalType.SHORT

    rm = RiskManager(
        equity=request.equity,
        max_leverage=request.max_leverage,
    )
    sizing = rm.calculate_position_size(
        entry_price=request.entry_price,
        stop_price=request.stop_price,
        direction=direction,
        current_exposure=request.current_exposure,
        win_rate=request.win_rate,
        avg_win_loss_ratio=request.avg_win_loss_ratio,
        method=request.method,
    )

    return PositionSizeResponse(
        size_notional=sizing.size_notional,
        size_contracts=sizing.size_contracts,
        leverage=sizing.leverage,
        risk_amount=sizing.risk_amount,
        risk_pct=sizing.risk_pct,
        margin_required=sizing.margin_required,
    )


@router.post("/limits/var")
async def calculate_var(request: VaRRequest) -> VaRResponse:
    """Calculate Value-at-Risk.

    Supports historical (empirical) and parametric (normal) methods.
    """
    if request.method == "parametric":
        result = RiskManager.calculate_parametric_var(request.returns)
    else:
        result = RiskManager.calculate_historical_var(request.returns)

    return VaRResponse(
        var_95=result.var_95,
        var_99=result.var_99,
        cvar_95=result.cvar_95,
        method=result.method,
    )


@router.get("/limits")
async def get_risk_limits() -> Dict[str, Any]:
    """Get current risk limit configuration."""
    from app.config import settings

    return {
        "max_leverage": settings.max_leverage,
        "risk_per_trade_min": settings.risk_per_trade_min,
        "risk_per_trade_max": settings.risk_per_trade_max,
        "max_total_exposure_pct": settings.max_total_exposure_pct,
        "universe": settings.universe_list,
    }
