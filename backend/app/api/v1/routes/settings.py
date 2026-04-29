"""User settings routes: get and update per-user strategy/risk configuration."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.dependencies import get_db
from app.models.user import User
from app.models.user_settings import UserSettings

router = APIRouter()


class UserSettingsResponse(BaseModel):
    rsi_period: int = 14
    rsi_regime_bullish_threshold: float = 55.0
    rsi_regime_bearish_threshold: float = 45.0
    rsi_signal_long_pullback_low: float = 40.0
    rsi_signal_long_pullback_high: float = 48.0
    rsi_signal_long_reclaim: float = 50.0
    rsi_signal_short_bounce_low: float = 52.0
    rsi_signal_short_bounce_high: float = 60.0
    rsi_signal_short_lose: float = 50.0
    rsi_exit_partial_r: float = 1.5
    rsi_exit_breakeven_r: float = 1.0
    rsi_exit_max_hours: int = 36
    risk_per_trade_min: float = 0.0025
    risk_per_trade_max: float = 0.0075
    max_leverage: int = 3
    max_total_exposure_pct: float = 0.30
    universe: List[str] = ["BTC", "ETH", "SOL"]
    has_zai_api_key: bool = False


class UpdateSettingsRequest(BaseModel):
    rsi_period: Optional[int] = None
    rsi_regime_bullish_threshold: Optional[float] = None
    rsi_regime_bearish_threshold: Optional[float] = None
    rsi_signal_long_pullback_low: Optional[float] = None
    rsi_signal_long_pullback_high: Optional[float] = None
    rsi_signal_long_reclaim: Optional[float] = None
    rsi_signal_short_bounce_low: Optional[float] = None
    rsi_signal_short_bounce_high: Optional[float] = None
    rsi_signal_short_lose: Optional[float] = None
    rsi_exit_partial_r: Optional[float] = None
    rsi_exit_breakeven_r: Optional[float] = None
    rsi_exit_max_hours: Optional[int] = None
    risk_per_trade_min: Optional[float] = None
    risk_per_trade_max: Optional[float] = None
    max_leverage: Optional[int] = Field(None, ge=1, le=10)
    max_total_exposure_pct: Optional[float] = Field(None, ge=0.0, le=1.0)
    universe: Optional[str] = None
    zai_api_key: Optional[str] = None


async def _get_or_create_settings(
    user_id: str, db: AsyncSession
) -> UserSettings:
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        await db.flush()
    return settings


def _to_response(s: UserSettings) -> UserSettingsResponse:
    return UserSettingsResponse(
        rsi_period=s.rsi_period,
        rsi_regime_bullish_threshold=s.rsi_regime_bullish_threshold,
        rsi_regime_bearish_threshold=s.rsi_regime_bearish_threshold,
        rsi_signal_long_pullback_low=s.rsi_signal_long_pullback_low,
        rsi_signal_long_pullback_high=s.rsi_signal_long_pullback_high,
        rsi_signal_long_reclaim=s.rsi_signal_long_reclaim,
        rsi_signal_short_bounce_low=s.rsi_signal_short_bounce_low,
        rsi_signal_short_bounce_high=s.rsi_signal_short_bounce_high,
        rsi_signal_short_lose=s.rsi_signal_short_lose,
        rsi_exit_partial_r=s.rsi_exit_partial_r,
        rsi_exit_breakeven_r=s.rsi_exit_breakeven_r,
        rsi_exit_max_hours=s.rsi_exit_max_hours,
        risk_per_trade_min=s.risk_per_trade_min,
        risk_per_trade_max=s.risk_per_trade_max,
        max_leverage=s.max_leverage,
        max_total_exposure_pct=s.max_total_exposure_pct,
        universe=[sym.strip() for sym in s.universe.split(",") if sym.strip()],
        has_zai_api_key=bool(s.zai_api_key),
    )


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserSettingsResponse:
    s = await _get_or_create_settings(str(current_user.id), db)
    return _to_response(s)


@router.put("", response_model=UserSettingsResponse)
async def update_settings(
    request: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserSettingsResponse:
    s = await _get_or_create_settings(str(current_user.id), db)

    update_data = request.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(s, field, value)

    await db.flush()
    return _to_response(s)
