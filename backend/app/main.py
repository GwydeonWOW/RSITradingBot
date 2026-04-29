"""FastAPI application entry point.

Configures the app with CORS, route includes, and startup/shutdown
lifecycle events.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.routes import health, strategies, signals, orders, risk, reports, ai, auth, wallets, settings as settings_routes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="RSI Trading Bot API for Hyperliquid",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route includes
app.include_router(health.router, tags=["health"])
app.include_router(strategies.router, prefix="/v1/strategies", tags=["strategies"])
app.include_router(signals.router, prefix="/v1/signals", tags=["signals"])
app.include_router(orders.router, prefix="/v1/orders", tags=["orders"])
app.include_router(risk.router, prefix="/v1/risk", tags=["risk"])
app.include_router(reports.router, prefix="/v1/reports", tags=["reports"])
app.include_router(ai.router, prefix="/v1/ai", tags=["ai"])
app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(wallets.router, prefix="/v1/wallets", tags=["wallets"])
app.include_router(settings_routes.router, prefix="/v1/settings", tags=["settings"])
