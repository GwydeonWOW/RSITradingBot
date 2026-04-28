"""AI service for exception classification via z.ai.

Provides integration with an external AI API (z.ai) for classifying
market anomalies and exceptions that the rule-based RSI system cannot
handle. Used for regime break detection, black swan events, and
unusual market microstructure patterns.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassificationResult:
    """Output of an AI exception classification."""

    category: str
    confidence: float
    explanation: str
    recommended_action: str
    metadata: Dict[str, Any]


class AIService:
    """Client for the z.ai exception classification API.

    Usage:
        service = AIService(api_key="...", api_url="https://api.z.ai/v1")
        result = await service.classify_exception(
            market_context={...},
            signal_data={...},
            exception_type="regime_break"
        )
    """

    def __init__(
        self,
        api_key: str = "",
        api_url: str = "https://api.z.ai/v1",
        timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._api_url = api_url.rstrip("/")
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._api_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
        return self._client

    async def classify_exception(
        self,
        market_context: Dict[str, Any],
        signal_data: Dict[str, Any],
        exception_type: str,
    ) -> Optional[ClassificationResult]:
        """Classify a market exception using the AI model.

        Args:
            market_context: Current market state (prices, RSI, regime, etc.).
            signal_data: The signal that triggered the exception check.
            exception_type: Type of exception to classify.

        Returns:
            ClassificationResult, or None if the API call fails.
        """
        if not self._api_key:
            logger.warning("z.ai API key not configured, skipping classification")
            return None

        payload = {
            "model": "classification-v1",
            "input": {
                "exception_type": exception_type,
                "market_context": market_context,
                "signal_data": signal_data,
            },
            "parameters": {
                "categories": [
                    "regime_break",
                    "black_swan",
                    "liquidity_crisis",
                    "microstructure_anomaly",
                    "normal_volatility",
                    "news_driven",
                ],
            },
        }

        try:
            client = await self._get_client()
            response = await client.post("/classify", json=payload)
            response.raise_for_status()

            data = response.json()
            return ClassificationResult(
                category=data.get("category", "unknown"),
                confidence=data.get("confidence", 0.0),
                explanation=data.get("explanation", ""),
                recommended_action=data.get("recommended_action", "hold"),
                metadata=data.get("metadata", {}),
            )
        except httpx.HTTPStatusError as exc:
            logger.error("z.ai API error: %s - %s", exc.response.status_code, exc.response.text)
        except httpx.RequestError as exc:
            logger.error("z.ai request failed: %s", exc)
        except Exception as exc:
            logger.error("Unexpected AI service error: %s", exc, exc_info=True)

        return None

    async def analyze_signal_quality(
        self,
        signal: Dict[str, Any],
        historical_performance: Dict[str, Any],
    ) -> Optional[ClassificationResult]:
        """Assess signal quality against historical patterns.

        Args:
            signal: The current signal data.
            historical_performance: Aggregated historical performance metrics.

        Returns:
            ClassificationResult with quality assessment.
        """
        if not self._api_key:
            return None

        payload = {
            "model": "signal-quality-v1",
            "input": {
                "signal": signal,
                "historical_performance": historical_performance,
            },
        }

        try:
            client = await self._get_client()
            response = await client.post("/analyze/signal-quality", json=payload)
            response.raise_for_status()

            data = response.json()
            return ClassificationResult(
                category=data.get("quality_tier", "unknown"),
                confidence=data.get("confidence", 0.0),
                explanation=data.get("explanation", ""),
                recommended_action=data.get("recommended_action", "proceed"),
                metadata=data.get("metadata", {}),
            )
        except Exception as exc:
            logger.error("Signal quality analysis failed: %s", exc)
            return None

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.close()
