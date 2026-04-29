"""AI service for exception classification via z.ai chat completions.

Provides integration with the z.ai API (glm-5.1 model) for classifying
market anomalies and exceptions that the rule-based RSI system cannot
handle. Used for regime break detection, black swan events, and
unusual market microstructure patterns.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_CLASSIFY = """\
You are a crypto-market risk classifier for an automated RSI trading bot.
Given market context, signal data, and an exception type, classify the
situation and recommend an action.

Respond ONLY with valid JSON matching this schema:
{
  "severity": "low" | "medium" | "high" | "critical",
  "class": "regime_break" | "black_swan" | "liquidity_crisis"
           | "microstructure_anomaly" | "normal_volatility" | "news_driven",
  "probable_root_cause": "<one-sentence explanation>",
  "allowed_action": "proceed" | "reduce_size" | "pause_entry" | "flatten_all"
}

Be concise. No prose outside the JSON."""

SYSTEM_PROMPT_SIGNAL = """\
You are a signal-quality assessor for an RSI-based crypto trading bot.
Given the current signal and historical performance data, rate the signal quality.

Respond ONLY with valid JSON matching this schema:
{
  "quality_tier": "A" | "B" | "C" | "D",
  "confidence": <float 0.0-1.0>,
  "explanation": "<one-sentence explanation>",
  "recommended_action": "proceed" | "reduce_size" | "skip"
}

Be concise. No prose outside the JSON."""


@dataclass(frozen=True)
class ClassificationResult:
    """Output of an AI exception classification."""

    category: str
    confidence: float
    explanation: str
    recommended_action: str
    metadata: Dict[str, Any]


class AIService:
    """Client for the z.ai chat completions API.

    Uses the glm-5.1 model with JSON response mode for structured
    exception classification and signal quality assessment.

    Usage:
        service = AIService(api_key="...", api_url="https://api.z.ai/api/paas/v4")
        result = await service.classify_exception(
            market_context={...},
            signal_data={...},
            exception_type="regime_break"
        )
    """

    def __init__(
        self,
        api_key: str = "",
        api_url: str = "https://api.z.ai/api/paas/v4",
        timeout: float = 15.0,
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

    async def _chat(self, system_prompt: str, user_content: str) -> Optional[str]:
        """Send a chat completion request and return the message content."""
        client = await self._get_client()
        payload = {
            "model": "glm-5.1",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
        }

        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_json(raw: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from the model response, handling markdown fences."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    async def classify_exception(
        self,
        market_context: Dict[str, Any],
        signal_data: Dict[str, Any],
        exception_type: str,
    ) -> Optional[ClassificationResult]:
        """Classify a market exception using z.ai glm-5.1.

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

        user_content = json.dumps({
            "exception_type": exception_type,
            "market_context": market_context,
            "signal_data": signal_data,
        })

        try:
            raw = await self._chat(SYSTEM_PROMPT_CLASSIFY, user_content)
            if not raw:
                return None

            parsed = self._parse_json(raw)
            if not parsed:
                logger.error("z.ai returned invalid JSON: %s", raw[:200])
                return None

            severity = parsed.get("severity", "unknown")
            cls = parsed.get("class", "unknown")
            cause = parsed.get("probable_root_cause", "")
            action = parsed.get("allowed_action", "pause_entry")

            return ClassificationResult(
                category=f"{severity}:{cls}",
                confidence=0.8 if severity != "critical" else 0.95,
                explanation=cause,
                recommended_action=action,
                metadata={"raw": parsed},
            )
        except httpx.HTTPStatusError as exc:
            logger.error("z.ai API error: %s - %s", exc.response.status_code, exc.response.text)
        except httpx.RequestError as exc:
            logger.error("z.ai request failed: %s", exc)
        except (KeyError, IndexError) as exc:
            logger.error("z.ai unexpected response format: %s", exc)
        except Exception as exc:
            logger.error("Unexpected AI service error: %s", exc, exc_info=True)

        return None

    async def analyze_signal_quality(
        self,
        signal: Dict[str, Any],
        historical_performance: Dict[str, Any],
    ) -> Optional[ClassificationResult]:
        """Assess signal quality against historical patterns using z.ai.

        Args:
            signal: The current signal data.
            historical_performance: Aggregated historical performance metrics.

        Returns:
            ClassificationResult with quality assessment.
        """
        if not self._api_key:
            return None

        user_content = json.dumps({
            "signal": signal,
            "historical_performance": historical_performance,
        })

        try:
            raw = await self._chat(SYSTEM_PROMPT_SIGNAL, user_content)
            if not raw:
                return None

            parsed = self._parse_json(raw)
            if not parsed:
                logger.error("z.ai returned invalid JSON for signal quality: %s", raw[:200])
                return None

            return ClassificationResult(
                category=parsed.get("quality_tier", "D"),
                confidence=parsed.get("confidence", 0.0),
                explanation=parsed.get("explanation", ""),
                recommended_action=parsed.get("recommended_action", "skip"),
                metadata={"raw": parsed},
            )
        except Exception as exc:
            logger.error("Signal quality analysis failed: %s", exc)
            return None

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.close()
