"""Unit tests for the AI provider pattern.

The base class (prompt building, JSON extraction, validation, the actionable
check) is exercised through a tiny fake subclass so we never call a real API.
The Groq/Anthropic adapters are tested with injected fake SDK clients that
mimic each SDK's response shape and error type.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import anthropic
import groq
import pytest
from app.config import Settings
from app.services.ai import (
    AIRequestError,
    AIResponseError,
    AnalysisContext,
    AnthropicProvider,
    GroqProvider,
    SignalDraft,
    build_ai_provider,
)
from app.services.ai.base import BaseAIProvider
from app.services.indicators import IndicatorSnapshot
from app.services.market_data import Candle

_VALID_BUY = (
    '{"direction":"buy","confidence":0.8,"entry":1.10,'
    '"stop_loss":1.09,"take_profits":[1.12,1.13],"rationale":"uptrend"}'
)


def _context() -> AnalysisContext:
    candle = Candle(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        open=Decimal("1.10"),
        high=Decimal("1.12"),
        low=Decimal("1.09"),
        close=Decimal("1.11"),
    )
    return AnalysisContext(
        symbol="EURUSD",
        timeframe="1h",
        indicators=IndicatorSnapshot(last_close=1.11, rsi_14=55.0),
        recent_candles=[candle],
    )


class _FakeProvider(BaseAIProvider):
    provider_name = "fake"

    def __init__(self, reply: str) -> None:
        self.model = "fake-1"
        self._reply = reply
        self.system: str | None = None
        self.user: str | None = None

    async def _complete(self, *, system: str, user: str) -> str:
        self.system = system
        self.user = user
        return self._reply

    async def aclose(self) -> None:
        return None


# ── BaseAIProvider.analyze ───────────────────────────────────────────────────


async def test_analyze_returns_signal_draft():
    provider = _FakeProvider(_VALID_BUY)
    draft = await provider.analyze(_context())

    assert isinstance(draft, SignalDraft)
    assert draft.direction == "buy"
    assert draft.entry == Decimal("1.10")
    assert draft.take_profits == [Decimal("1.12"), Decimal("1.13")]
    # The prompt actually carried the instrument + indicators.
    assert "EURUSD" in provider.user
    assert "direction" in provider.system


async def test_analyze_rejects_directional_signal_without_entry():
    reply = '{"direction":"sell","confidence":0.7,"entry":null,"take_profits":[]}'
    provider = _FakeProvider(reply)
    with pytest.raises(AIResponseError, match="entry"):
        await provider.analyze(_context())


async def test_analyze_allows_neutral_without_prices():
    reply = '{"direction":"neutral","confidence":0.4,"rationale":"chop"}'
    draft = await _FakeProvider(reply).analyze(_context())
    assert draft.direction == "neutral"
    assert draft.entry is None


# ── _extract_json ────────────────────────────────────────────────────────────


def test_extract_json_plain_object():
    assert BaseAIProvider._extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_strips_code_fence():
    raw = '```json\n{"a": 1}\n```'
    assert BaseAIProvider._extract_json(raw) == {"a": 1}


def test_extract_json_slices_surrounding_prose():
    raw = 'Sure! Here is the signal:\n{"direction": "neutral"}\nHope that helps.'
    assert BaseAIProvider._extract_json(raw) == {"direction": "neutral"}


def test_extract_json_empty_raises():
    with pytest.raises(AIResponseError, match="Empty"):
        BaseAIProvider._extract_json("   ")


def test_extract_json_no_object_raises():
    with pytest.raises(AIResponseError):
        BaseAIProvider._extract_json("no json here")


def test_extract_json_array_is_not_an_object():
    with pytest.raises(AIResponseError):
        BaseAIProvider._extract_json("[1, 2, 3]")


# ── SignalDraft validation ───────────────────────────────────────────────────


def test_confidence_above_one_is_clamped():
    assert SignalDraft(direction="neutral", confidence=1.4).confidence == 1.0


def test_confidence_negative_is_clamped_to_zero():
    assert SignalDraft(direction="neutral", confidence=-3).confidence == 0.0


def test_negative_entry_rejected():
    with pytest.raises(ValueError, match="positive"):
        SignalDraft(direction="buy", confidence=0.5, entry=Decimal("-1"))


def test_too_many_take_profits_rejected():
    with pytest.raises(ValueError):
        SignalDraft(
            direction="buy",
            confidence=0.5,
            entry=Decimal("1.1"),
            take_profits=[Decimal("1.2"), Decimal("1.3"), Decimal("1.4"), Decimal("1.5")],
        )


def test_negative_take_profit_rejected():
    with pytest.raises(ValueError, match="positive"):
        SignalDraft(
            direction="buy",
            confidence=0.5,
            entry=Decimal("1.1"),
            take_profits=[Decimal("-1.2")],
        )


# ── Factory ──────────────────────────────────────────────────────────────────


def _settings(**overrides) -> Settings:
    base = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "ai_api_key": "k",
        "twelve_data_api_key": "k",
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


async def test_factory_builds_groq_by_default():
    provider = build_ai_provider(_settings(ai_provider="groq"))
    assert isinstance(provider, GroqProvider)
    await provider.aclose()


async def test_factory_builds_anthropic_when_configured():
    provider = build_ai_provider(_settings(ai_provider="anthropic", ai_model="claude-sonnet-4-6"))
    assert isinstance(provider, AnthropicProvider)
    assert provider.model == "claude-sonnet-4-6"
    await provider.aclose()


# ── Groq adapter ─────────────────────────────────────────────────────────────


class _GroqCompletions:
    def __init__(self, outer: _FakeGroqClient) -> None:
        self._outer = outer

    async def create(self, **kwargs):
        self._outer.calls.append(kwargs)
        if self._outer.error is not None:
            raise self._outer.error
        message = SimpleNamespace(content=self._outer.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeGroqClient:
    def __init__(self, *, content: str = _VALID_BUY, error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=_GroqCompletions(self))


async def test_groq_complete_returns_content_and_requests_json_mode():
    client = _FakeGroqClient()
    provider = GroqProvider("k", "llama-x", client=client)
    out = await provider._complete(system="sys", user="usr")
    assert out == _VALID_BUY
    assert client.calls[0]["response_format"] == {"type": "json_object"}
    assert client.calls[0]["model"] == "llama-x"


async def test_groq_error_is_wrapped():
    client = _FakeGroqClient(error=groq.GroqError("boom"))
    provider = GroqProvider("k", "llama-x", client=client)
    with pytest.raises(AIRequestError, match="Groq"):
        await provider._complete(system="s", user="u")


# ── Anthropic adapter ────────────────────────────────────────────────────────


class _AnthropicMessages:
    def __init__(self, outer: _FakeAnthropicClient) -> None:
        self._outer = outer

    async def create(self, **kwargs):
        self._outer.calls.append(kwargs)
        if self._outer.error is not None:
            raise self._outer.error
        blocks = [SimpleNamespace(type="text", text=self._outer.text)]
        return SimpleNamespace(content=blocks)


class _FakeAnthropicClient:
    def __init__(self, *, text: str = _VALID_BUY, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls: list[dict] = []
        self.messages = _AnthropicMessages(self)


async def test_anthropic_complete_concatenates_text_and_passes_system():
    client = _FakeAnthropicClient(text=_VALID_BUY)
    provider = AnthropicProvider("k", "claude-x", client=client)
    out = await provider._complete(system="SYSTEM", user="USER")
    assert out == _VALID_BUY
    assert client.calls[0]["system"] == "SYSTEM"
    assert client.calls[0]["messages"] == [{"role": "user", "content": "USER"}]


async def test_anthropic_empty_text_raises_response_error():
    client = _FakeAnthropicClient(text="")
    provider = AnthropicProvider("k", "claude-x", client=client)
    with pytest.raises(AIResponseError):
        await provider._complete(system="s", user="u")


async def test_anthropic_error_is_wrapped():
    client = _FakeAnthropicClient(error=anthropic.AnthropicError("boom"))
    provider = AnthropicProvider("k", "claude-x", client=client)
    with pytest.raises(AIRequestError, match="Anthropic"):
        await provider._complete(system="s", user="u")
