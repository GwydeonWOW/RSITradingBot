"""Signal evaluation routes."""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import settings
from app.core.auth import get_current_user
from app.models.user import User

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
