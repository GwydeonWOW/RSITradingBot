"""Signal evaluation routes."""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user
from app.dependencies import get_db
from app.models.bot_state import BotState
from app.models.user import User
from app.models.position import Position, PositionStatus

router = APIRouter()
logger = logging.getLogger(__name__)


class SignalEvaluateRequest(BaseModel):
    symbol: str = "BTC"


class SignalEvaluateResponse(BaseModel):
    regime: Optional[str] = None
    rsi_4h: Optional[float] = None
    rsi_1h: Optional[float] = None
    signal: Optional[Dict[str, Any]] = None
    sizing: Optional[Dict[str, Any]] = None


async def _fetch_candles(coin: str, interval: str, hours_back: int) -> List[float]:
    """Fetch candle closes from Hyperliquid."""
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (hours_back * 60 * 60 * 1000)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={
                    "type": "candleSnapshot",
                    "req": {
                        "coin": coin,
                        "interval": interval,
                        "startTime": start_ms,
                        "endTime": now_ms,
                    },
                },
            )
            resp.raise_for_status()
            candles = resp.json()

        return [float(c["c"]) for c in candles]
    except Exception as exc:
        logger.error("Failed to fetch %s %s candles: %s", coin, interval, exc)
        return []


@router.post("/evaluate")
async def evaluate_signal(
    request: SignalEvaluateRequest,
    current_user: User = Depends(get_current_user),
) -> SignalEvaluateResponse:
    """Evaluate the RSI strategy using real candle data from Hyperliquid."""
    from app.services.strategy_service import StrategyService

    # Fetch 4H candles (5 days = ~30 candles, enough for RSI-14)
    closes_4h = await _fetch_candles(request.symbol, "4h", 120)
    # Fetch 1H candles (2 days = ~48 candles)
    closes_1h = await _fetch_candles(request.symbol, "1h", 48)
    # Fetch latest 15m candle for current price
    closes_15m = await _fetch_candles(request.symbol, "15m", 1)

    price_15m = closes_15m[-1] if closes_15m else (closes_1h[-1] if closes_1h else 0.0)
    is_bullish_15m = len(closes_15m) >= 2 and closes_15m[-1] >= closes_15m[-2]

    if not closes_4h or not closes_1h or price_15m == 0.0:
        return SignalEvaluateResponse()

    service = StrategyService(
        equity=10000.0,
        current_exposure=0.0,
    )

    result = service.evaluate(
        closes_4h=closes_4h,
        closes_1h=closes_1h,
        price_15m=price_15m,
        is_bullish_15m=is_bullish_15m,
    )

    return SignalEvaluateResponse(**result)


class BotStatusResponse(BaseModel):
    running: bool
    regime: Optional[str] = None
    signal_stage: Optional[str] = None
    signal_type: Optional[str] = None
    rsi_4h: Optional[float] = None
    rsi_1h: Optional[float] = None
    last_price: Optional[float] = None
    last_eval_at: Optional[str] = None
    open_positions: int = 0
    last_error: Optional[str] = None


@router.get("/bot-status", response_model=BotStatusResponse)
async def get_bot_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BotStatusResponse:
    """Get current bot engine status for the authenticated user."""
    from app.main import bot_engine

    result = await db.execute(
        select(BotState).where(BotState.user_id == current_user.id)
    )
    state = result.scalar_one_or_none()

    pos_result = await db.execute(
        select(Position).where(
            Position.user_id == current_user.id,
            Position.status.in_([PositionStatus.OPEN, PositionStatus.PARTIALLY_CLOSED]),
        )
    )
    open_positions = len(pos_result.scalars().all())

    if state is None:
        return BotStatusResponse(running=bot_engine.running, open_positions=open_positions)

    return BotStatusResponse(
        running=bot_engine.running,
        regime=state.last_regime,
        signal_stage=state.signal_stage,
        signal_type=state.signal_type,
        rsi_4h=state.last_rsi_4h,
        rsi_1h=state.last_rsi_1h,
        last_price=state.last_price,
        last_eval_at=state.last_eval_at.isoformat() if state.last_eval_at else None,
        open_positions=open_positions,
        last_error=state.last_error,
    )


@router.post("/bot-start")
async def start_bot(current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    from app.main import bot_engine
    await bot_engine.start_bot()
    return {"status": "started"}


@router.post("/bot-stop")
async def stop_bot(current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    from app.main import bot_engine
    await bot_engine.stop_bot()
    return {"status": "stopped"}


class BotLogEntry(BaseModel):
    id: str
    level: str
    message: str
    symbol: str
    regime: Optional[str] = None
    rsi_4h: Optional[float] = None
    rsi_1h: Optional[float] = None
    price: Optional[float] = None
    signal_stage: Optional[str] = None
    signal_type: Optional[str] = None
    created_at: str


class BotLogResponse(BaseModel):
    logs: List[BotLogEntry]
    count: int


@router.get("/bot-logs", response_model=BotLogResponse)
async def get_bot_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BotLogResponse:
    from app.models.bot_log import BotLog
    result = await db.execute(
        select(BotLog)
        .where(BotLog.user_id == current_user.id)
        .order_by(BotLog.created_at.desc())
        .limit(min(limit, 200))
    )
    logs = result.scalars().all()
    return BotLogResponse(
        logs=[
            BotLogEntry(
                id=str(l.id),
                level=l.level,
                message=l.message,
                symbol=l.symbol,
                regime=l.regime,
                rsi_4h=l.rsi_4h,
                rsi_1h=l.rsi_1h,
                price=l.price,
                signal_stage=l.signal_stage,
                signal_type=l.signal_type,
                created_at=l.created_at.isoformat() if l.created_at else "",
            )
            for l in logs
        ],
        count=len(logs),
    )
