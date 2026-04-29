"""AI exception classification routes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.dependencies import get_db
from app.models.user import User
from app.models.user_settings import UserSettings

router = APIRouter()


class ExceptionClassifyRequest(BaseModel):
    """Request body for exception classification."""

    exception_type: str  # "regime_break", "liquidity_crisis", etc.
    market_context: Dict[str, Any] = Field(default_factory=dict)
    signal_data: Dict[str, Any] = Field(default_factory=dict)


class ExceptionClassifyResponse(BaseModel):
    """AI classification result."""

    category: Optional[str] = None
    confidence: Optional[float] = None
    explanation: Optional[str] = None
    recommended_action: Optional[str] = None
    error: Optional[str] = None


@router.post("/exceptions/classify")
async def classify_exception(
    request: ExceptionClassifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExceptionClassifyResponse:
    """Classify a market exception using the AI model.

    Uses the user's own z.ai API key from their settings.
    """
    from app.services.ai_service import AIService
    from app.config import settings

    # Get user's API key from their settings
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    user_settings = result.scalar_one_or_none()
    api_key = user_settings.zai_api_key if user_settings and user_settings.zai_api_key else ""

    if not api_key:
        return ExceptionClassifyResponse(
            error="z.ai API key not configured. Add it in Settings.",
        )

    service = AIService(
        api_key=api_key,
        api_url=settings.zai_api_url,
    )

    try:
        result = await service.classify_exception(
            market_context=request.market_context,
            signal_data=request.signal_data,
            exception_type=request.exception_type,
        )

        if result is None:
            return ExceptionClassifyResponse(
                error="AI classification unavailable. Check API key configuration.",
            )

        return ExceptionClassifyResponse(
            category=result.category,
            confidence=result.confidence,
            explanation=result.explanation,
            recommended_action=result.recommended_action,
        )
    finally:
        await service.close()
