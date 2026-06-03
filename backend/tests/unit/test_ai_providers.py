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
    DualSignalDraft,
    GroqProvider,
    PriorSignal,
    SignalDraft,
    TimeframeView,
    build_ai_provider,
)
from app.services.ai.base import BaseAIProvider
from app.services.indicators import IndicatorSnapshot
from app.services.market_data import Candle

# A single signal object — still used as a raw ``_complete`` payload by the
# provider-adapter tests (which never parse it).
_VALID_BUY = (
    '{"direction":"buy","confidence":0.8,"entry":1.10,'
    '"stop_loss":1.09,"take_profits":[1.12,1.13],"rationale":"uptrend"}'
)

# The real analyze() contract: a dual object with a scalp and a swing.
_VALID_DUAL = (
    '{"scalp":{"direction":"buy","confidence":0.6,"entry":1.105,'
    '"stop_loss":1.10,"take_profits":[1.11],"rationale":"scalp long"},'
    '"swing":{"direction":"sell","confidence":0.8,"entry":1.10,'
    '"stop_loss":1.12,"take_profits":[1.08,1.06],"rationale":"swing short"}}'
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
        primary_timeframe="1h",
        views=(
            TimeframeView(
                timeframe="1h",
                indicators=IndicatorSnapshot(last_close=1.11, rsi_14=55.0),
                recent_candles=[candle],
            ),
        ),
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


async def test_analyze_returns_dual_signal_draft():
    provider = _FakeProvider(_VALID_DUAL)
    dual = await provider.analyze(_context())

    assert isinstance(dual, DualSignalDraft)
    assert dual.scalp.direction == "buy"
    assert dual.scalp.entry == Decimal("1.105")
    assert dual.swing.direction == "sell"
    assert dual.swing.take_profits == [Decimal("1.08"), Decimal("1.06")]
    # The prompt actually carried the instrument, and the contract names both styles.
    assert "EURUSD" in provider.user
    assert "scalp" in provider.system and "swing" in provider.system


async def test_user_prompt_includes_prior_signals_for_keep_or_adjust():
    base = _context()
    context = AnalysisContext(
        symbol=base.symbol,
        primary_timeframe=base.primary_timeframe,
        views=base.views,
        current_scalp=PriorSignal(
            direction="buy",
            confidence=0.6,
            entry=Decimal("1.10"),
            stop_loss=Decimal("1.09"),
            take_profits=(Decimal("1.12"),),
            generated_at="2026-06-01T12:00:00+00:00",
        ),
        current_swing=None,
    )
    provider = _FakeProvider(_VALID_DUAL)
    await provider.analyze(context)

    assert "Current open signals" in provider.user
    assert "SCALP: buy" in provider.user
    assert "SWING: none open yet" in provider.user


async def test_user_prompt_renders_all_timeframes_high_to_low():
    candle = Candle(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        open=Decimal("1.10"),
        high=Decimal("1.12"),
        low=Decimal("1.09"),
        close=Decimal("1.11"),
    )
    context = AnalysisContext(
        symbol="XAUUSD",
        primary_timeframe="1h",
        # Deliberately out of order to prove the prompt re-sorts high→low.
        views=(
            TimeframeView(timeframe="5m", indicators=IndicatorSnapshot(), recent_candles=[candle]),
            TimeframeView(timeframe="1d", indicators=IndicatorSnapshot(), recent_candles=[candle]),
            TimeframeView(timeframe="1h", indicators=IndicatorSnapshot(), recent_candles=[candle]),
        ),
    )
    provider = _FakeProvider(_VALID_DUAL)
    await provider.analyze(context)

    user = provider.user
    # Every timeframe appears, the primary is flagged, and 1d is rendered
    # before 5m (top-down order, not config order).
    assert "Timeframe: 1d" in user
    assert "Timeframe: 1h — PRIMARY" in user
    assert "Timeframe: 5m" in user
    assert user.index("Timeframe: 1d") < user.index("Timeframe: 5m")


async def test_analyze_rejects_signal_without_entry():
    # The swing draft is directional but carries no entry — must be rejected.
    reply = (
        '{"scalp":{"direction":"buy","confidence":0.6,"entry":1.1,'
        '"stop_loss":1.0,"take_profits":[1.2]},'
        '"swing":{"direction":"sell","confidence":0.7,"entry":null,"take_profits":[]}}'
    )
    provider = _FakeProvider(reply)
    with pytest.raises(AIResponseError, match="entry"):
        await provider.analyze(_context())


async def test_analyze_rejects_neutral_signal():
    # Always-on product rule: a neutral reply is rejected (fails the pair), not
    # persisted as a no-trade.
    reply = (
        '{"scalp":{"direction":"neutral","confidence":0.4,"rationale":"chop"},'
        '"swing":{"direction":"buy","confidence":0.6,"entry":1.1,'
        '"stop_loss":1.0,"take_profits":[1.2]}}'
    )
    with pytest.raises(AIResponseError, match="directional"):
        await _FakeProvider(reply).analyze(_context())


# ── _extract_json ────────────────────────────────────────────────────────────


def test_round_indicators_trims_human_scale_but_keeps_sub_unit_precision():
    rounded = BaseAIProvider._round_indicators(
        {
            "rsi_14": 33.04176178,
            "ema_200": 2338.512,
            "atr_14": 0.00143217,
            "macd": -0.00071,
            "candles_analyzed": 200,
            "as_of": "2026-06-03",
        }
    )
    assert rounded["rsi_14"] == 33.04  # human-scale → 2 decimals
    assert rounded["ema_200"] == 2338.51
    assert rounded["atr_14"] == 0.001432  # sub-unit value keeps precision
    assert rounded["macd"] == -0.00071
    assert rounded["candles_analyzed"] == 200  # ints untouched
    assert rounded["as_of"] == "2026-06-03"  # non-numbers untouched


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
