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
    DualSignalDraft,
    PriorSignal,
    SignalDirection,
    SignalDraft,
    TimeframeView,
)
from app.services.ai.groq_provider import GroqProvider

if TYPE_CHECKING:
    from app.config import Settings

__all__ = [
    "AIError",
    "AIProvider",
    "AIRequestError",
    "AIResponseError",
    "AnalysisContext",
    "AnthropicProvider",
    "DualSignalDraft",
    "GroqProvider",
    "PriorSignal",
    "SignalDirection",
    "SignalDraft",
    "TimeframeView",
    "build_ai_provider",
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
    }
    match settings.ai_provider:
        case "groq":
            return GroqProvider(settings.ai_api_key, **common)
        case "anthropic":
            return AnthropicProvider(settings.ai_api_key, **common)
