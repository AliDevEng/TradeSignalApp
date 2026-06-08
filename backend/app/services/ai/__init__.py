"""AI service package.

Public surface: the :class:`AIProvider` contract, its ``AnalysisContext``
input / ``SignalDraft`` output, the error hierarchy, and a single factory that
maps the configured ``ai_provider`` to a concrete implementation. The factory
is the only place that knows which SDK backs which provider name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base import (
    AIError,
    AIProvider,
    AIRequestError,
    AIResponseError,
    AnalysisContext,
    AnalysisResult,
    CompletionResult,
    DualSignalDraft,
    PriorPerformance,
    PriorSignal,
    SignalDirection,
    SignalDraft,
    TimeframeView,
    TokenUsage,
)
from app.services.ai.groq_provider import GroqProvider
from app.services.ai.pricing import estimate_cost_usd

if TYPE_CHECKING:
    from app.config import Settings

__all__ = [
    "AIError",
    "AIProvider",
    "AIRequestError",
    "AIResponseError",
    "AnalysisContext",
    "AnalysisResult",
    "AnthropicProvider",
    "CompletionResult",
    "DualSignalDraft",
    "GroqProvider",
    "PriorPerformance",
    "PriorSignal",
    "SignalDirection",
    "SignalDraft",
    "TimeframeView",
    "TokenUsage",
    "build_ai_provider",
    "estimate_cost_usd",
]


def build_ai_provider(settings: Settings) -> AIProvider:
    """Construct the provider selected by ``settings.ai_provider``.

    Exhaustive over the ``AIProvider`` config Literal — extending that Literal
    without adding a branch here is a type error, so a new provider can never
    be silently unsupported at runtime.
    """
    common = {
        "model": settings.ai_model,
        "temperature": settings.ai_temperature,
        "max_tokens": settings.ai_max_tokens,
        "timeout_seconds": settings.ai_timeout_seconds,
        "prompt_candle_window": settings.ai_prompt_candle_window,
    }
    match settings.ai_provider:
        case "groq":
            return GroqProvider(settings.ai_api_key, **common)
        case "anthropic":
            return AnthropicProvider(settings.ai_api_key, **common)
