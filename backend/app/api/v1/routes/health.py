"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "service": "rsi-trading-bot"}


@router.get("/health/detailed")
async def health_check_detailed():
    """Detailed health check with dependency status."""
    return {
        "status": "ok",
        "service": "rsi-trading-bot",
        "version": "0.1.0",
        "dependencies": {
            "postgresql": "not_checked",
            "redis": "not_checked",
            "clickhouse": "not_checked",
        },
    }
