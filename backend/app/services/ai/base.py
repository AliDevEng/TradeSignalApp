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
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.services import ServiceError
from app.services.indicators.calculator import IndicatorSnapshot
from app.services.market_data.base import Candle

logger = logging.getLogger(__name__)

SignalDirection = Literal["buy", "sell", "neutral"]

# Cap on take-profit levels the model may return (TP1/TP2/TP3 in the product).
MAX_TAKE_PROFITS: Final[int] = 3
# Most recent candles included in the prompt. Enough for the model to see
# near-term price action without blowing the token budget on ancient bars the
# indicators already summarise.
_PROMPT_CANDLE_WINDOW: Final[int] = 30

_JSON_FENCE_RE: Final[re.Pattern[str]] = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

# Persona/method/risk-rules live in an editable Markdown file next to this
# module so prompt engineering can iterate without code changes; the strict
# JSON output contract is appended from code (below) so it can never drift from
# the ``SignalDraft`` schema it must satisfy.
_PROMPT_DIR: Final[Path] = Path(__file__).parent / "prompts"
_SYSTEM_PROMPT_FILE: Final[str] = "hedge_fund_analyst.md"

# Relative magnitude of each timeframe, used to present them top-down
# (highest → lowest) regardless of the order they were configured in.
_TIMEFRAME_MINUTES: Final[dict[str, int]] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


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
class TimeframeView:
    """One timeframe's evidence: its indicator snapshot + recent candles.

    The unit of a multi-timeframe analysis — the model receives several of
    these per instrument and reasons across them top-down.
    """

    timeframe: str
    indicators: IndicatorSnapshot
    recent_candles: list[Candle]


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    """Everything the model needs to reason about one pair, in one place.

    Carries several :class:`TimeframeView` s so the provider can perform a
    top-down, multi-timeframe read. ``primary_timeframe`` is the decision
    timeframe a resulting signal is framed on and recorded against.

    Frozen so a provider can't accidentally mutate shared inputs when the
    same context is (in future) fanned out to multiple models for comparison.
    """

    symbol: str
    primary_timeframe: str
    views: tuple[TimeframeView, ...]


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


class AIProvider(abc.ABC):
    """Turns an :class:`AnalysisContext` into a :class:`SignalDraft`."""

    provider_name: str
    model: str

    @abc.abstractmethod
    async def analyze(self, context: AnalysisContext) -> SignalDraft: ...

    @abc.abstractmethod
    async def aclose(self) -> None:
        """Release the underlying SDK/HTTP client. Idempotent."""


class BaseAIProvider(AIProvider):
    """Template implementation: prompt → ``_complete`` → parse.

    Concrete providers implement :meth:`_complete` (and :meth:`aclose`); they
    do not override :meth:`analyze`, so prompt and parsing behaviour stays
    identical across providers.
    """

    async def analyze(self, context: AnalysisContext) -> SignalDraft:
        system = self._build_system_prompt()
        user = self._build_user_prompt(context)
        raw = await self._complete(system=system, user=user)
        draft = self._parse_response(raw)
        self._assert_actionable(draft)
        logger.info(
            "AI signal for %s/%s: %s (confidence=%.2f) via %s/%s",
            context.symbol,
            context.primary_timeframe,
            draft.direction,
            draft.confidence,
            self.provider_name,
            self.model,
        )
        return draft

    @abc.abstractmethod
    async def _complete(self, *, system: str, user: str) -> str:
        """Send the prompt to the provider and return the raw text reply.

        Implementations must translate provider/transport exceptions into
        :class:`AIRequestError` so callers only ever catch the service base.
        """

    # ── Prompt construction ──────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        """Editable persona (from file) + the strict JSON output contract.

        The contract is built here, not in the file, so the documented keys
        always match what :class:`SignalDraft` will accept on the way back.
        """
        keys = ", ".join(
            [
                '"direction" (one of "buy","sell","neutral")',
                '"confidence" (number 0..1)',
                '"entry" (number or null)',
                '"stop_loss" (number or null)',
                f'"take_profits" (array of up to {MAX_TAKE_PROFITS} numbers, ordered TP1..TP3)',
                '"rationale" (short string)',
            ]
        )
        contract = (
            "## Output contract\n"
            "Respond with a STRICT JSON object and nothing else (no markdown, no "
            f"prose). Required keys: {keys}. "
            'For a "buy" or "sell", provide entry, stop_loss and at least one '
            "take_profit consistent with the direction (for a buy: "
            "stop_loss < entry < take_profits; for a sell: the reverse). "
            'For "neutral", prices may be null.'
        )
        return f"{_load_system_persona()}\n\n{contract}"

    def _build_user_prompt(self, context: AnalysisContext) -> str:
        # Present timeframes highest → lowest so the model reads bias before
        # trigger, regardless of configured order.
        views = sorted(
            context.views,
            key=lambda v: _TIMEFRAME_MINUTES.get(v.timeframe, 0),
            reverse=True,
        )
        blocks = []
        for view in views:
            ind = view.indicators.model_dump(mode="json")
            candles = self._render_candles(view.recent_candles)
            primary = " — PRIMARY / decision timeframe" if (
                view.timeframe == context.primary_timeframe
            ) else ""
            blocks.append(
                f"=== Timeframe: {view.timeframe}{primary} ===\n"
                f"Indicators (latest):\n{json.dumps(ind, indent=2, default=str)}\n\n"
                f"Recent candles (oldest first, up to {_PROMPT_CANDLE_WINDOW}):\n{candles}"
            )
        order = ", ".join(v.timeframe for v in views)
        return (
            f"Instrument: {context.symbol}\n"
            f"Primary (decision) timeframe: {context.primary_timeframe}\n"
            f"Timeframes provided (high → low): {order}\n\n"
            + "\n\n".join(blocks)
            + "\n\nPerform a top-down multi-timeframe analysis and return the JSON signal now."
        )

    @staticmethod
    def _render_candles(candles: list[Candle]) -> str:
        window = candles[-_PROMPT_CANDLE_WINDOW:]
        lines = [
            f"{c.timestamp.isoformat()} O:{c.open} H:{c.high} L:{c.low} C:{c.close}" for c in window
        ]
        return "\n".join(lines) if lines else "(none)"

    # ── Response parsing ─────────────────────────────────────────────────

    def _parse_response(self, raw: str) -> SignalDraft:
        payload = self._extract_json(raw)
        try:
            return SignalDraft.model_validate(payload)
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
    def _assert_actionable(draft: SignalDraft) -> None:
        """A directional call without an entry isn't tradeable.

        Enforced here (not in the model) because it's a *semantic* rule about
        signals, distinct from the field-shape validation the model owns —
        and it keeps ``SignalDraft`` reusable for non-directional contexts.
        """
        if draft.direction in ("buy", "sell") and draft.entry is None:
            raise AIResponseError(f"{draft.direction!r} signal is missing an entry price")
