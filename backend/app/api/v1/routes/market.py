"""Market data routes — proxy to Hyperliquid REST API."""

from __future__ import annotations

import logging
from typing import List

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class MarketTicker(BaseModel):
    symbol: str
    mid_price: float


class MarketResponse(BaseModel):
    tickers: List[MarketTicker]
    count: int


@router.get("", response_model=MarketResponse)
async def get_market_data() -> MarketResponse:
    """Fetch current mid prices from Hyperliquid."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "allMids"},
            )
            resp.raise_for_status()
            mids = resp.json()

        tickers = []
        for symbol, price_str in mids.items():
            if symbol.startswith("@") or symbol.endswith("/USDC"):
                continue
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                continue
            tickers.append(MarketTicker(symbol=symbol, mid_price=price))

        return MarketResponse(tickers=tickers, count=len(tickers))

    except Exception as exc:
        logger.error("Failed to fetch market data from Hyperliquid: %s", exc)
        return MarketResponse(tickers=[], count=0)
