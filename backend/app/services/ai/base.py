"""AI provider contract + the shared analysis template.

The provider-specific code (Groq, Anthropic) is deliberately tiny: each
concrete class implements exactly one method — ``_complete`` — that turns a
(system, user) prompt pair into a raw string. *Everything* else — building the
prompt, extracting JSON from a chatty response, validating it into a
:class:`SignalDraft`, clamping confidence — lives here, once.

That is the Template Method pattern, chosen on purpose: prompt engineering and
response hardening are where the subtle bugs live, and we never want two
copies of that logic drifting apart. Adding a third provider should be a
~20-line file, not a fork of the parsing rules.

The provider returns a ``SignalDraft`` — *not* a persisted ``Signal``. Mapping
a draft onto the ORM model (assigning ``pair_id``, ``generated_at``, the
``analysis_run_id``, persistence) is the controller's job in Iteration 4. The
service layer must not import the database.
"""

from __future__ import annotations

import abc
import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.services import ServiceError
from app.services.calendar import EconomicEvent
from app.services.indicators.calculator import IndicatorSnapshot
from app.services.market_data.base import Candle
from app.services.structure import StructureSnapshot
from app.timeframes import timeframe_minutes

logger = logging.getLogger(__name__)

SignalDirection = Literal["buy", "sell", "neutral"]

# Cap on take-profit levels the model may return (TP1/TP2/TP3 in the product).
MAX_TAKE_PROFITS: Final[int] = 3
# Cap on the self-reported risk/trap notes a signal may carry.
MAX_RISKS: Final[int] = 5
# Default count of recent candles per timeframe in the prompt. Enough for the
# model to see near-term price action without blowing the token budget on
# ancient bars the indicators already summarise. Overridable per instance (via
# the provider constructor / ``ai_prompt_candle_window`` setting) so the budget
# can be tuned to the provider tier — e.g. trimmed to fit a free tier's
# tokens-per-minute cap, widened on a paid one.
_DEFAULT_PROMPT_CANDLE_WINDOW: Final[int] = 20

_JSON_FENCE_RE: Final[re.Pattern[str]] = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _compact_json(value: Any) -> str:
    """Serialise to JSON with no whitespace — indentation is pure wasted tokens.

    The model parses compact JSON identically to a pretty-printed block, so the
    indent/newlines an LLM never needs are dropped before the prompt is metered
    against the provider's token budget.
    """
    return json.dumps(value, separators=(",", ":"), default=str)

# Persona/method/risk-rules live in an editable Markdown file next to this
# module so prompt engineering can iterate without code changes; the strict
# JSON output contract is appended from code (below) so it can never drift from
# the ``SignalDraft`` schema it must satisfy.
_PROMPT_DIR: Final[Path] = Path(__file__).parent / "prompts"
_SYSTEM_PROMPT_FILE: Final[str] = "hedge_fund_analyst.md"


@lru_cache(maxsize=1)
def _load_system_persona() -> str:
    """Read the persona prompt file once and cache it for the process."""
    return (_PROMPT_DIR / _SYSTEM_PROMPT_FILE).read_text(encoding="utf-8").strip()


class AIError(ServiceError):
    """Base for AI-provider failures."""


class AIRequestError(AIError):
    """The provider call itself failed (network, auth, timeout, rate limit)."""


class AIResponseError(AIError):
    """The provider replied, but the content was not a usable signal."""


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token counts for one provider call — the basis for cost tracking.

    Both fields are optional because not every provider/response exposes them;
    a caller treats ``None`` as "unknown" rather than zero. Kept SDK-free (plain
    ints) so the controller can persist usage without importing any provider type.
    """

    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None and self.completion_tokens is None:
            return None
        return (self.prompt_tokens or 0) + (self.completion_tokens or 0)


@dataclass(frozen=True, slots=True)
class CompletionResult:
    """A raw provider completion: the reply text plus optional token usage.

    ``_complete`` returns this (rather than a bare string) so usage can be
    threaded back to the controller for cost tracking without the parsing layer
    or the controller ever importing an SDK response type.
    """

    text: str
    usage: TokenUsage | None = None


@dataclass(frozen=True, slots=True)
class TimeframeView:
    """One timeframe's evidence: its indicator snapshot + recent candles.

    The unit of a multi-timeframe analysis — the model receives several of
    these per instrument and reasons across them top-down.
    """

    timeframe: str
    indicators: IndicatorSnapshot
    recent_candles: list[Candle]
    # Computed price structure for this timeframe (swing pivots, nearest
    # support/resistance, range). ``None`` leaves the structure block out, so the
    # prompt is unchanged for callers that don't supply it.
    structure: StructureSnapshot | None = None


@dataclass(frozen=True, slots=True)
class PriorSignal:
    """A compact snapshot of the pair's current signal of a given style.

    Fed back into the prompt so the model can *keep or adjust* the open idea
    against fresh data rather than starting from scratch each run. Carries only
    what the model needs to recognise its previous call — not the full ORM row.
    """

    direction: str
    confidence: float
    entry: Decimal | None
    stop_loss: Decimal | None
    take_profits: tuple[Decimal, ...]
    generated_at: str  # ISO 8601


@dataclass(frozen=True, slots=True)
class PriorPerformance:
    """The pair/style's recent realised track record, fed back to the model.

    This closes the learning loop: instead of guessing how reliable its calls
    are, the model is shown how its *own* recent signals of this style actually
    resolved, so it can calibrate confidence against reality. ``confidence_bias``
    is the mean stated confidence minus the realised win-rate — positive means the
    style has been over-confident. All ratio fields are ``None`` when there is no
    closed history yet (``closed == 0``).
    """

    closed: int
    win_rate: float | None
    avg_r: Decimal | None
    confidence_bias: float | None


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    """Everything the model needs to reason about one pair, in one place.

    Carries several :class:`TimeframeView` s so the provider can perform a
    top-down, multi-timeframe read. ``primary_timeframe`` is the decision
    timeframe a resulting signal is framed on and recorded against.

    ``current_scalp`` / ``current_swing`` are the pair's currently-open signals
    (if any) of each style, fed back so the model keeps or adjusts them.

    ``scalp_timeframes`` / ``swing_timeframes`` are the timeframes each style is
    *framed* on. They label the evidence (every ``view`` is still provided to
    the model, but the prompt tells it which frames anchor the scalp's levels
    and which anchor the swing's). Empty tuples leave the blocks unlabelled.

    Frozen so a provider can't accidentally mutate shared inputs when the
    same context is (in future) fanned out to multiple models for comparison.
    """

    symbol: str
    primary_timeframe: str
    views: tuple[TimeframeView, ...]
    current_scalp: PriorSignal | None = None
    current_swing: PriorSignal | None = None
    scalp_timeframes: tuple[str, ...] = ()
    swing_timeframes: tuple[str, ...] = ()
    # The pair's recent realised track record per style (Iteration 9 feedback
    # loop). ``None`` leaves the performance block out of the prompt entirely.
    scalp_performance: PriorPerformance | None = None
    swing_performance: PriorPerformance | None = None
    # Upcoming high-impact macro events relevant to this instrument (Iteration 10
    # news awareness). Empty leaves the news block out, so the prompt is
    # unchanged when the calendar is disabled.
    events: tuple[EconomicEvent, ...] = ()


class SignalDraft(BaseModel):
    """Structured trade idea returned by a provider.

    A *draft* because it carries no identity or persistence concerns — those
    are added by the controller. Prices are ``Decimal`` to match the signals
    schema and avoid float drift between the model's number and the stored
    one.
    """

    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    entry: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profits: list[Decimal] = Field(default_factory=list, max_length=MAX_TAKE_PROFITS)
    rationale: str | None = None
    # The model's own trap-check: the concrete ways this idea could fail (stop
    # hunt, news, over-extension, fighting the higher-TF trend). Surfaced for the
    # user and folded into the rationale; the *actionable* decision is the
    # deterministic gate's, not these self-reported risks. Capped so a verbose
    # model can't bloat the row.
    risks: list[str] = Field(default_factory=list, max_length=MAX_RISKS)

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, value: Any) -> Any:
        """Clamp to [0, 1] rather than reject.

        Models occasionally emit a slightly out-of-range value (1.2, -0.1);
        clamping degrades gracefully where rejecting would discard an
        otherwise-valid signal. We deliberately do *not* try to guess that a
        value like 85 "means" 85% — that heuristic is ambiguous (is 1.4 over-
        confident, or 1.4%?) and silently corrupts confidence. A model that
        ignores the documented 0..1 range gets clamped, not reinterpreted.
        """
        try:
            number = float(value)
        except (TypeError, ValueError):
            return value
        return min(max(number, 0.0), 1.0)

    @field_validator("entry", "stop_loss")
    @classmethod
    def _price_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("price must be positive")
        return value

    @field_validator("take_profits")
    @classmethod
    def _take_profits_positive(cls, value: list[Decimal]) -> list[Decimal]:
        if any(tp <= 0 for tp in value):
            raise ValueError("take-profit prices must be positive")
        return value

    @model_validator(mode="after")
    def _coherent_geometry(self) -> SignalDraft:
        """Reject levels that contradict the direction.

        The prompt demands a consistent ladder — for a buy, ``stop_loss < entry
        < TP1 < TP2 < TP3`` (the reverse for a sell). Pydantic and the provider's
        forced-tool schema validate field *shapes* (positive, ≤3 TPs) but not
        these cross-field relationships, so without this a model could emit a
        "buy" whose stop sits above entry: it would render a nonsensical R:R card
        *and* be unscoreable (the outcome evaluator can't define risk on a
        wrong-sided stop), silently dropping out of the track record. Rejecting
        here surfaces as an :class:`AIResponseError`, which the controller
        contains as a per-pair failure for that run rather than persisting a
        broken signal.

        Only meaningful for a directional draft with an entry; a ``neutral`` or
        entry-less draft is left to :meth:`BaseAIProvider._assert_actionable`.
        ``None`` levels are skipped, so a draft with fewer than three TPs (or no
        stop) is checked only on the levels it actually carries.
        """
        if self.direction not in ("buy", "sell") or self.entry is None:
            return self
        ladder = [self.stop_loss, self.entry, *self.take_profits]
        present = [level for level in ladder if level is not None]
        ascending = self.direction == "buy"
        for lower, higher in pairwise(present):
            in_order = lower < higher if ascending else lower > higher
            if not in_order:
                arrow = (
                    "stop < entry < TP1 < TP2 < TP3"
                    if ascending
                    else ("stop > entry > TP1 > TP2 > TP3")
                )
                raise ValueError(
                    f"{self.direction} levels must satisfy {arrow}; "
                    f"got {[str(level) for level in present]}"
                )
        return self


class DualSignalDraft(BaseModel):
    """The model's full output for one pair: a scalp *and* a swing idea.

    Each run frames two trade horizons from the same multi-timeframe evidence —
    a short-term ``scalp`` and a higher-timeframe ``swing`` — returned together
    in one call so the model reasons about them jointly (and we pay one request
    per pair, not two).
    """

    scalp: SignalDraft
    swing: SignalDraft


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """The provider's full output for one pair: the dual draft + token usage.

    ``analyze`` returns this so the controller gets the signals *and* the usage
    it needs for cost tracking, without importing any SDK type. ``usage`` is
    ``None`` when the provider didn't report token counts.
    """

    dual: DualSignalDraft
    usage: TokenUsage | None = None


class AIProvider(abc.ABC):
    """Turns an :class:`AnalysisContext` into an :class:`AnalysisResult`."""

    provider_name: str
    model: str

    @abc.abstractmethod
    async def analyze(self, context: AnalysisContext) -> AnalysisResult: ...

    @abc.abstractmethod
    async def aclose(self) -> None:
        """Release the underlying SDK/HTTP client. Idempotent."""


class BaseAIProvider(AIProvider):
    """Template implementation: prompt → ``_complete`` → parse.

    Concrete providers implement :meth:`_complete` (and :meth:`aclose`); they
    do not override :meth:`analyze`, so prompt and parsing behaviour stays
    identical across providers.
    """

    #: Recent candles per timeframe included in the prompt. A class default so a
    #: provider that doesn't set it (and the test fakes) still works; concrete
    #: providers override it per instance from settings.
    _prompt_candle_window: int = _DEFAULT_PROMPT_CANDLE_WINDOW

    async def analyze(self, context: AnalysisContext) -> AnalysisResult:
        system = self._build_system_prompt()
        user = self._build_user_prompt(context)
        completion = await self._complete(system=system, user=user)
        dual = self._parse_response(completion.text)
        self._assert_actionable(dual.scalp, style="scalp")
        self._assert_actionable(dual.swing, style="swing")
        logger.info(
            "AI signals for %s: scalp=%s (%.2f) swing=%s (%.2f) via %s/%s (tokens=%s)",
            context.symbol,
            dual.scalp.direction,
            dual.scalp.confidence,
            dual.swing.direction,
            dual.swing.confidence,
            self.provider_name,
            self.model,
            completion.usage.total_tokens if completion.usage else "n/a",
        )
        return AnalysisResult(dual=dual, usage=completion.usage)

    @abc.abstractmethod
    async def _complete(self, *, system: str, user: str) -> CompletionResult:
        """Send the prompt to the provider and return the reply text + usage.

        Implementations must translate provider/transport exceptions into
        :class:`AIRequestError` so callers only ever catch the service base, and
        should attach a :class:`TokenUsage` when the response reports one.
        """

    # ── Prompt construction ──────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        """Editable persona (from file) + the strict JSON output contract.

        The contract is built here, not in the file, so the documented keys
        always match what :class:`DualSignalDraft` will accept on the way back.
        """
        signal_keys = ", ".join(
            [
                '"direction" (one of "buy","sell")',
                '"confidence" (number 0..1 — how sure you are)',
                '"entry" (number)',
                '"stop_loss" (number)',
                f'"take_profits" (array of 1..{MAX_TAKE_PROFITS} numbers, ordered TP1..TP3)',
                '"rationale" (short string)',
                f'"risks" (array of up to {MAX_RISKS} short strings — the concrete '
                "ways THIS trade could fail: stop hunt, news, over-extension, "
                "counter-trend)",
            ]
        )
        contract = (
            "## Output contract\n"
            "Respond with a STRICT JSON object and nothing else (no markdown, no "
            'prose). The object MUST have exactly two keys: "scalp" and "swing", '
            "each a signal object with these keys: "
            f"{signal_keys}. "
            'BOTH signals are mandatory and BOTH must be directional ("buy" or '
            '"sell") — never "neutral", never null prices. Express any lack of '
            "conviction through a LOW confidence value, not by refusing to trade. "
            "Levels must be internally consistent with the direction (for a buy: "
            "stop_loss < entry < TP1 < TP2 < TP3; for a sell: the reverse). Anchor "
            "every level to the PROVIDED structure (swing highs/lows, "
            "support/resistance) and never invent a level the data does not show. "
            'Before committing, run a trap-check and record it in "risks"; if the '
            "setup is poor (weak reward:risk, counter-trend, news imminent) keep the "
            "directional bias but lower its confidence — a separate gate decides "
            "whether it is actually tradeable. The "
            '"scalp" is a short-term idea framed on the lower timeframes (tighter '
            'stop, nearer targets); the "swing" is a higher-timeframe idea (wider '
            "stop, extended targets). They may differ in direction."
        )
        return f"{_load_system_persona()}\n\n{contract}"

    def _build_user_prompt(self, context: AnalysisContext) -> str:
        # Present timeframes highest → lowest so the model reads bias before
        # trigger, regardless of configured order.
        views = sorted(
            context.views,
            key=lambda v: timeframe_minutes(v.timeframe),
            reverse=True,
        )
        scalp_set = set(context.scalp_timeframes)
        swing_set = set(context.swing_timeframes)
        blocks = []
        for view in views:
            ind = self._round_indicators(view.indicators.model_dump(mode="json"))
            candles = self._render_candles(view.recent_candles)
            role = self._frame_role(view.timeframe, scalp_set, swing_set)
            primary = (
                " — PRIMARY / decision timeframe"
                if (view.timeframe == context.primary_timeframe)
                else ""
            )
            structure = self._render_structure(view.structure)
            blocks.append(
                f"=== Timeframe: {view.timeframe}{role}{primary} ===\n"
                f"Indicators (latest):\n{_compact_json(ind)}\n"
                f"{structure}\n"
                f"Recent candles (oldest first, up to {self._prompt_candle_window}):\n{candles}"
            )
        order = ", ".join(v.timeframe for v in views)
        framing = self._render_framing(context)
        prior = self._render_prior_signals(context)
        performance = self._render_performance(context)
        news = self._render_news(context)
        return (
            f"Instrument: {context.symbol}\n"
            f"Primary (decision) timeframe: {context.primary_timeframe}\n"
            f"Timeframes provided (high → low): {order}\n"
            + framing
            + news
            + "\n\n"
            + "\n\n".join(blocks)
            + f"\n\n{prior}"
            + performance
            + "\n\nPerform a top-down multi-timeframe analysis and return the JSON "
            "object with both a scalp and a swing signal now."
        )

    @staticmethod
    def _render_structure(structure: StructureSnapshot | None) -> str:
        """Render the computed price structure for a timeframe block.

        Omitted (empty string) when no structure was supplied or none could be
        derived, so unlabelled callers and short series are unchanged. When
        present it gives the model real levels to anchor stops/targets to.
        """
        if structure is None or structure.is_empty:
            return ""
        levels = structure.to_dict()
        return "Structure (computed — anchor levels to these):\n" + _compact_json(levels)

    @staticmethod
    def _render_news(context: AnalysisContext) -> str:
        """Render upcoming high-impact events so the model can de-risk near them.

        Omitted entirely when there are no events (calendar disabled or nothing
        scheduled), keeping the prompt identical to before the feature.
        """
        if not context.events:
            return ""
        lines = "\n".join(
            f"- {event.label()} at {event.scheduled_at.isoformat()}" for event in context.events
        )
        return (
            "\n\n⚠️ Upcoming high-impact events (widen stops / lower confidence; a "
            "release can spike price through a tight stop):\n" + lines
        )

    @staticmethod
    def _render_performance(context: AnalysisContext) -> str:
        """Render the pair's recent realised track record so the model can learn.

        Omitted entirely (empty string) when neither style has performance data,
        so the prompt is unchanged for callers that don't supply it. When present,
        it nudges the model to calibrate confidence against its own results rather
        than its priors.
        """
        scalp = context.scalp_performance
        swing = context.swing_performance
        if scalp is None and swing is None:
            return ""

        def one(label: str, perf: PriorPerformance | None) -> str:
            if perf is None or perf.closed == 0:
                return f"- {label}: no closed history yet."
            win = f"{perf.win_rate * 100:.0f}%" if perf.win_rate is not None else "n/a"
            avg_r = f"{perf.avg_r:+.2f}R" if perf.avg_r is not None else "n/a"
            bias = ""
            if perf.confidence_bias is not None:
                pp = perf.confidence_bias * 100
                tone = "over-confident" if pp > 0 else "under-confident"
                bias = f" | confidence bias {pp:+.0f}pp ({tone})"
            return f"- {label}: {perf.closed} closed | win-rate {win} | avg {avg_r}{bias}"

        return (
            "\n\nYour recent track record on this pair (LEARN from it — if a style "
            "has been over-confident, lower its confidence; if its win-rate is poor, "
            "be more selective or rethink the bias):\n"
            f"{one('SCALP', scalp)}\n"
            f"{one('SWING', swing)}"
        )

    @staticmethod
    def _frame_role(timeframe: str, scalp_set: set[str], swing_set: set[str]) -> str:
        """Tag a timeframe block with the style(s) it frames.

        Returns an empty string when no frame sets were supplied (so the prompt
        is unchanged for callers that don't label frames, e.g. older tests).
        """
        in_scalp = timeframe in scalp_set
        in_swing = timeframe in swing_set
        if not scalp_set and not swing_set:
            return ""
        if in_scalp and in_swing:
            return " [SCALP+SWING frame]"
        if in_scalp:
            return " [SCALP frame]"
        if in_swing:
            return " [SWING frame]"
        return " [context only]"

    @staticmethod
    def _render_framing(context: AnalysisContext) -> str:
        """One line telling the model which frames anchor each style's levels.

        Omitted entirely when no frame sets were supplied, so the prompt stays
        identical for unlabelled callers.
        """
        if not context.scalp_timeframes and not context.swing_timeframes:
            return ""
        scalp = ", ".join(context.scalp_timeframes) or "(none)"
        swing = ", ".join(context.swing_timeframes) or "(none)"
        return (
            f"\nScalp frame: {scalp} | Swing frame: {swing}\n"
            "Frame the SCALP's entry/stop/targets on the scalp-frame timeframes "
            "and the SWING's on the swing-frame timeframes. You may read every "
            "timeframe for directional bias, but anchor each style's levels to "
            "its own frame."
        )

    @staticmethod
    def _render_prior_signals(context: AnalysisContext) -> str:
        """Render the pair's currently-open signals so the model can keep/adjust.

        Without a prior signal of a given style, says so explicitly — the model
        should then open a fresh idea rather than assume continuity.
        """

        def one(label: str, prior: PriorSignal | None) -> str:
            if prior is None:
                return f"- {label}: none open yet — open a fresh idea."
            tps = ", ".join(str(tp) for tp in prior.take_profits) or "(none)"
            return (
                f"- {label}: {prior.direction} | confidence {prior.confidence:.2f} | "
                f"entry {prior.entry} | stop {prior.stop_loss} | TPs {tps} | "
                f"as of {prior.generated_at}"
            )

        return (
            "Current open signals (KEEP them if the fresh data still supports the "
            "idea; otherwise ADJUST levels/direction/confidence and say what "
            "changed in the rationale):\n"
            f"{one('SCALP', context.current_scalp)}\n"
            f"{one('SWING', context.current_swing)}"
        )

    @staticmethod
    def _round_indicators(indicators: dict[str, Any]) -> dict[str, Any]:
        """Trim indicator floats — and drop unset ones — before the model sees them.

        Indicator values carry full float precision (e.g. RSI 33.04176178), and
        the model tends to quote them verbatim in its rationale. Rounding here
        keeps cited numbers readable. Human-scale values (RSI, MACD/EMA on gold,
        prices) are capped at 2 decimals; sub-unit values (ATR/MACD on FX,
        ``bb_percent``) keep more precision so they don't collapse to ``0.0``.

        ``None`` fields (indicators not yet available early in a series) are
        omitted entirely: an absent key reads the same as a ``null`` to the model
        but costs no tokens, which matters against a provider's per-request budget.
        """

        def _round(value: Any) -> Any:
            if isinstance(value, float):
                return round(value, 2) if abs(value) >= 1 else round(value, 6)
            return value

        return {key: _round(value) for key, value in indicators.items() if value is not None}

    def _render_candles(self, candles: list[Candle]) -> str:
        window = candles[-self._prompt_candle_window :]
        lines = [
            f"{c.timestamp.isoformat()} O:{c.open} H:{c.high} L:{c.low} C:{c.close}" for c in window
        ]
        return "\n".join(lines) if lines else "(none)"

    # ── Response parsing ─────────────────────────────────────────────────

    def _parse_response(self, raw: str) -> DualSignalDraft:
        payload = self._extract_json(raw)
        try:
            return DualSignalDraft.model_validate(payload)
        except ValidationError as exc:
            raise AIResponseError(f"Signal JSON failed validation: {exc}") from exc

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        """Pull a JSON object out of a model reply.

        Handles three realities of LLM output: clean JSON, JSON wrapped in a
        ```json fence, and JSON with leading/trailing prose. Anything else is
        an :class:`AIResponseError` rather than a confusing ``KeyError`` later.
        """
        if not raw or not raw.strip():
            raise AIResponseError("Empty response from provider")

        text = raw.strip()
        fenced = _JSON_FENCE_RE.search(text)
        candidate = fenced.group(1) if fenced else text

        # If there's surrounding prose, slice the outermost {...}.
        if not candidate.lstrip().startswith("{"):
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start == -1 or end == -1 or end < start:
                raise AIResponseError("No JSON object found in response")
            candidate = candidate[start : end + 1]

        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise AIResponseError(f"Response was not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise AIResponseError("Response JSON was not an object")
        return parsed

    @staticmethod
    def _assert_actionable(draft: SignalDraft, *, style: str) -> None:
        """Every emitted signal must be a directional, tradeable call.

        Enforced here (not in the model) because it's a *semantic* rule about
        signals, distinct from the field-shape validation the model owns — and it
        keeps ``SignalDraft`` reusable for other contexts. The product now
        requires an always-on directional signal per style: a ``neutral`` or
        entry-less reply is rejected (it fails just this pair for this run, via
        the controller's per-pair containment) rather than silently producing
        nothing.
        """
        if draft.direction not in ("buy", "sell"):
            raise AIResponseError(
                f"{style} signal must be directional (buy/sell), got {draft.direction!r}"
            )
        if draft.entry is None:
            raise AIResponseError(f"{style} {draft.direction!r} signal is missing an entry price")
