"""Market data routes — proxy to Hyperliquid REST API."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class MarketTicker(BaseModel):
    symbol: str
    mid_price: float
    mark_price: float
    prev_day_px: float
    day_ntl_vlm: float
    funding: float
    open_interest: float


class MarketResponse(BaseModel):
    tickers: List[MarketTicker]
    count: int


@router.get("", response_model=MarketResponse)
async def get_market_data() -> MarketResponse:
    """Fetch current market data from Hyperliquid for all perpetuals."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch all mid prices
            mids_resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "allMids"},
            )
            mids_resp.raise_for_status()
            mids = mids_resp.json()

            # Fetch metadata (mark prices, volume, funding, etc.)
            meta_resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "meta"},
            )
            meta_resp.raise_for_status()
            meta = meta_resp.json()

            # Fetch funding rates
            funding_resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "fundingRates"},
            )
            funding_resp.raise_for_status()
            funding_data = funding_resp.json()

        # Build universe from metadata
        universe = meta.get("universe", [])
        funding_map = {f.get("coin", ""): float(f.get("fundingRate", 0)) for f in funding_data}

        tickers = []
        for i, asset in enumerate(universe):
            name = asset.get("name", "")
            mid = float(mids.get(name, 0))
            mark_px = float(asset.get("markPx", 0)) if asset.get("markPx") else mid
            prev_day = float(asset.get("prevDayPx", 0)) if asset.get("prevDayPx") else 0
            volume = float(asset.get("dayNtlVlm", 0)) if asset.get("dayNtlVlm") else 0
            oi = float(asset.get("openInterest", 0)) if asset.get("openInterest") else 0

            tickers.append(MarketTicker(
                symbol=name,
                mid_price=mid,
                mark_price=mark_px if mark_px else mid,
                prev_day_px=prev_day,
                day_ntl_vlm=volume,
                funding=funding_map.get(name, 0.0),
                open_interest=oi,
            ))

        return MarketResponse(tickers=tickers, count=len(tickers))

    except httpx.HTTPError as exc:
        logger.error("Failed to fetch market data from Hyperliquid: %s", exc)
        return MarketResponse(tickers=[], count=0)
