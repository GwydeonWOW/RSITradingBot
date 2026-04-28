"""AI exception classification routes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

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
async def classify_exception(request: ExceptionClassifyRequest) -> ExceptionClassifyResponse:
    """Classify a market exception using the AI model.

    Sends market context and signal data to the z.ai API for
    classification. Returns the category, confidence, and
    recommended action.
    """
    from app.services.ai_service import AIService
    from app.config import settings

    service = AIService(
        api_key=settings.zai_api_key,
        api_url=settings.zai_api_url,
    )

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

    await service.close()
