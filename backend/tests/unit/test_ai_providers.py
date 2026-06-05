"""Unit tests for the AI provider pattern.

The base class (prompt building, JSON extraction, validation, the actionable
check) is exercised through a tiny fake subclass so we never call a real API.
The Groq/Anthropic adapters are tested with injected fake SDK clients that
mimic each SDK's response shape and error type.
"""

from __future__ import annotations

import json
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
    AnalysisResult,
    AnthropicProvider,
    CompletionResult,
    DualSignalDraft,
    GroqProvider,
    PriorPerformance,
    PriorSignal,
    SignalDraft,
    TimeframeView,
    TokenUsage,
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

    def __init__(self, reply: str, *, usage: TokenUsage | None = None) -> None:
        self.model = "fake-1"
        self._reply = reply
        self._usage = usage
        self.system: str | None = None
        self.user: str | None = None

    async def _complete(self, *, system: str, user: str) -> CompletionResult:
        self.system = system
        self.user = user
        return CompletionResult(text=self._reply, usage=self._usage)

    async def aclose(self) -> None:
        return None


# ── BaseAIProvider.analyze ───────────────────────────────────────────────────


async def test_analyze_returns_dual_signal_draft():
    provider = _FakeProvider(_VALID_DUAL)
    result = await provider.analyze(_context())

    assert isinstance(result, AnalysisResult)
    dual = result.dual
    assert isinstance(dual, DualSignalDraft)
    assert dual.scalp.direction == "buy"
    assert dual.scalp.entry == Decimal("1.105")
    assert dual.swing.direction == "sell"
    assert dual.swing.take_profits == [Decimal("1.08"), Decimal("1.06")]
    # The prompt actually carried the instrument, and the contract names both styles.
    assert "EURUSD" in provider.user
    assert "scalp" in provider.system and "swing" in provider.system


async def test_analyze_threads_token_usage_through():
    provider = _FakeProvider(_VALID_DUAL, usage=TokenUsage(prompt_tokens=120, completion_tokens=45))
    result = await provider.analyze(_context())

    assert result.usage is not None
    assert result.usage.prompt_tokens == 120
    assert result.usage.completion_tokens == 45
    assert result.usage.total_tokens == 165


async def test_analyze_usage_is_none_when_provider_reports_none():
    result = await _FakeProvider(_VALID_DUAL).analyze(_context())
    assert result.usage is None


async def test_user_prompt_includes_recent_performance_when_supplied():
    base = _context()
    context = AnalysisContext(
        symbol=base.symbol,
        primary_timeframe=base.primary_timeframe,
        views=base.views,
        scalp_performance=PriorPerformance(
            closed=10, win_rate=0.4, avg_r=Decimal("0.15"), confidence_bias=0.2
        ),
        swing_performance=None,
    )
    provider = _FakeProvider(_VALID_DUAL)
    await provider.analyze(context)

    assert "Your recent track record" in provider.user
    assert "SCALP: 10 closed | win-rate 40% | avg +0.15R" in provider.user
    assert "over-confident" in provider.user
    assert "SWING: no closed history yet" in provider.user


async def test_user_prompt_omits_performance_when_absent():
    provider = _FakeProvider(_VALID_DUAL)
    await provider.analyze(_context())
    assert "Your recent track record" not in provider.user


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


async def test_user_prompt_labels_scalp_and_swing_frames():
    candle = Candle(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        open=Decimal("1.10"),
        high=Decimal("1.12"),
        low=Decimal("1.09"),
        close=Decimal("1.11"),
    )
    snap = IndicatorSnapshot()
    context = AnalysisContext(
        symbol="XAUUSD",
        primary_timeframe="1h",
        views=(
            TimeframeView(timeframe="5m", indicators=snap, recent_candles=[candle]),
            TimeframeView(timeframe="4h", indicators=snap, recent_candles=[candle]),
            TimeframeView(timeframe="1d", indicators=snap, recent_candles=[candle]),
        ),
        scalp_timeframes=("5m", "4h"),
        swing_timeframes=("4h", "1d"),
    )
    provider = _FakeProvider(_VALID_DUAL)
    await provider.analyze(context)

    user = provider.user
    # Each block carries its role; the shared 4h is tagged for both styles.
    assert "Timeframe: 5m [SCALP frame]" in user
    assert "Timeframe: 4h [SCALP+SWING frame]" in user
    assert "Timeframe: 1d [SWING frame]" in user
    # And the framing instruction lists each style's frame set.
    assert "Scalp frame: 5m, 4h" in user
    assert "Swing frame: 4h, 1d" in user


async def test_user_prompt_omits_frame_labels_when_unset():
    # No frame sets supplied → blocks stay unlabelled and no framing line appears.
    provider = _FakeProvider(_VALID_DUAL)
    await provider.analyze(_context())

    assert "[SCALP frame]" not in provider.user
    assert "Scalp frame:" not in provider.user


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


def test_buy_with_stop_above_entry_rejected():
    # A wrong-sided stop would be unscoreable (no defined risk) and nonsensical.
    with pytest.raises(ValueError, match="buy levels must satisfy"):
        SignalDraft(
            direction="buy",
            confidence=0.6,
            entry=Decimal("1.10"),
            stop_loss=Decimal("1.12"),
            take_profits=[Decimal("1.15")],
        )


def test_buy_with_non_monotonic_take_profits_rejected():
    with pytest.raises(ValueError, match="buy levels must satisfy"):
        SignalDraft(
            direction="buy",
            confidence=0.6,
            entry=Decimal("1.10"),
            stop_loss=Decimal("1.09"),
            take_profits=[Decimal("1.13"), Decimal("1.11")],
        )


def test_sell_levels_must_descend():
    with pytest.raises(ValueError, match="sell levels must satisfy"):
        SignalDraft(
            direction="sell",
            confidence=0.6,
            entry=Decimal("1.10"),
            stop_loss=Decimal("1.08"),  # stop should be ABOVE entry for a sell
            take_profits=[Decimal("1.05")],
        )


def test_coherent_buy_ladder_accepted():
    draft = SignalDraft(
        direction="buy",
        confidence=0.6,
        entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profits=[Decimal("1.11"), Decimal("1.12"), Decimal("1.13")],
    )
    assert draft.direction == "buy"


def test_geometry_skipped_for_entryless_or_neutral_draft():
    # No entry (neutral chop reply) — geometry can't apply; left to _assert_actionable.
    assert SignalDraft(direction="neutral", confidence=0.4).direction == "neutral"


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
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=self._outer.usage)


class _FakeGroqClient:
    def __init__(
        self,
        *,
        content: str = _VALID_BUY,
        error: Exception | None = None,
        usage: object | None = None,
    ) -> None:
        self.content = content
        self.error = error
        self.usage = usage
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=_GroqCompletions(self))


async def test_groq_complete_returns_content_and_requests_json_mode():
    client = _FakeGroqClient()
    provider = GroqProvider("k", "llama-x", client=client)
    out = await provider._complete(system="sys", user="usr")
    assert isinstance(out, CompletionResult)
    assert out.text == _VALID_BUY
    assert client.calls[0]["response_format"] == {"type": "json_object"}
    assert client.calls[0]["model"] == "llama-x"


async def test_groq_complete_captures_token_usage():
    usage = SimpleNamespace(prompt_tokens=200, completion_tokens=80)
    client = _FakeGroqClient(usage=usage)
    provider = GroqProvider("k", "llama-x", client=client)
    out = await provider._complete(system="s", user="u")
    assert out.usage == TokenUsage(prompt_tokens=200, completion_tokens=80)


async def test_groq_complete_usage_none_when_absent():
    out = await GroqProvider("k", "llama-x", client=_FakeGroqClient())._complete(
        system="s", user="u"
    )
    assert out.usage is None


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
        return SimpleNamespace(content=self._outer.blocks, usage=self._outer.usage)


class _FakeAnthropicClient:
    def __init__(
        self,
        *,
        text: str | None = _VALID_BUY,
        tool_input: dict | None = None,
        error: Exception | None = None,
        usage: object | None = None,
    ) -> None:
        self.error = error
        self.usage = usage
        self.calls: list[dict] = []
        blocks: list[SimpleNamespace] = []
        if tool_input is not None:
            blocks.append(
                SimpleNamespace(type="tool_use", name="emit_dual_signal", input=tool_input)
            )
        elif text is not None:
            blocks.append(SimpleNamespace(type="text", text=text))
        self.blocks = blocks
        self.messages = _AnthropicMessages(self)


async def test_anthropic_forces_the_signal_tool():
    client = _FakeAnthropicClient(text=_VALID_BUY)
    provider = AnthropicProvider("k", "claude-x", client=client)
    await provider._complete(system="SYSTEM", user="USER")

    call = client.calls[0]
    assert call["system"] == "SYSTEM"
    assert call["messages"] == [{"role": "user", "content": "USER"}]
    # A single forced tool whose schema is the dual-signal contract.
    assert call["tool_choice"] == {"type": "tool", "name": "emit_dual_signal"}
    assert call["tools"][0]["name"] == "emit_dual_signal"
    assert "scalp" in call["tools"][0]["input_schema"]["properties"]


async def test_anthropic_reads_structured_tool_output():
    payload = {
        "scalp": {"direction": "buy", "confidence": 0.6, "entry": 1.1, "take_profits": [1.2]},
        "swing": {"direction": "sell", "confidence": 0.7, "entry": 1.1, "take_profits": [1.0]},
    }
    client = _FakeAnthropicClient(text=None, tool_input=payload)
    provider = AnthropicProvider("k", "claude-x", client=client)
    out = await provider._complete(system="s", user="u")
    # The tool input is serialised back to JSON for the base parser.
    assert json.loads(out.text) == payload


async def test_anthropic_falls_back_to_text_without_a_tool_block():
    client = _FakeAnthropicClient(text=_VALID_BUY)
    out = await AnthropicProvider("k", "claude-x", client=client)._complete(system="s", user="u")
    assert out.text == _VALID_BUY


async def test_anthropic_captures_token_usage():
    usage = SimpleNamespace(input_tokens=300, output_tokens=90)
    client = _FakeAnthropicClient(text=_VALID_BUY, usage=usage)
    out = await AnthropicProvider("k", "claude-x", client=client)._complete(system="s", user="u")
    assert out.usage == TokenUsage(prompt_tokens=300, completion_tokens=90)


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
