"""The deterministic quality gate: bias → (should_trade, quality_score, reasons).

A bias becomes a trade only when the evidence supports acting *now*. The gate
turns that judgement into something testable and auditable rather than leaving it
to the model's mood:

* it computes the **reward:risk** to TP1 from the levels themselves;
* it raises **hard vetoes** (``should_trade = False``) for the textbook traps — a
  reward:risk below the floor, a high-impact news release inside the blackout
  window, or fighting a *strong* (trending-regime) higher-timeframe trend;
* it blends the surviving signal into a **quality score** in ``[0, 1]`` that
  rewards trend alignment, clean reward:risk and confirming divergence, and
  penalises a directionless (ranging) regime.

Everything here is pure: same evidence in, same verdict out. No IO, no ORM, no
provider types — so it is unit-tested as a table of cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Final

# ── Tunable weights (documented constants, not magic numbers) ─────────────────
# The quality score starts from the model's own confidence and is nudged by
# corroborating/contradicting evidence. Weights are deliberately modest so no
# single factor dominates a sane confidence read.
_W_TREND_ALIGNED: Final[float] = 0.15  # bias agrees with higher-TF trend
_W_TREND_AGAINST: Final[float] = -0.20  # bias fights the higher-TF trend
_W_RR_STRONG: Final[float] = 0.10  # reward:risk comfortably ≥ the "good" mark
_W_DIVERGENCE_CONFIRMS: Final[float] = 0.10  # divergence points the bias's way
_W_DIVERGENCE_CONTRADICTS: Final[float] = -0.10  # divergence points the other way
_W_RANGING_REGIME: Final[float] = -0.10  # directionless market, weaker edge

# A reward:risk at/above this is "clean" and earns the bonus.
_RR_STRONG: Final[float] = 2.0


@dataclass(frozen=True, slots=True)
class GateConfig:
    """Operator-tunable thresholds (sourced from ``Settings``)."""

    # Below this reward:risk to TP1 a setup is vetoed outright — the single most
    # common reason a "good-looking" trade loses money over time.
    min_reward_risk: float = 1.5
    # The quality score a surviving bias must clear to be marked actionable.
    quality_threshold: float = 0.5


@dataclass(frozen=True, slots=True)
class GateEvidence:
    """Everything the gate needs about one bias, as plain values (no ORM/SDK)."""

    direction: str  # "buy" | "sell"
    entry: Decimal
    stop_loss: Decimal | None
    take_profit_1: Decimal | None
    confidence: float
    # Bias of the highest analysed timeframe: "up" | "down" | None (unknown).
    higher_tf_trend: str | None = None
    # Regime of the decision timeframe: "trending" | "ranging" | "transitional" | None.
    regime: str | None = None
    # RSI divergence on the decision timeframe: "bullish" | "bearish" | None.
    rsi_divergence: str | None = None
    # A high-impact event is inside the news blackout window.
    news_blackout: bool = False
    # Human-readable label of the blackout event, for the veto reason.
    news_event: str | None = None


@dataclass(frozen=True, slots=True)
class GateVerdict:
    """The gate's decision for one bias."""

    should_trade: bool
    quality_score: float
    reward_risk: float | None
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """JSON-safe projection for the ``quality_snapshot`` column."""
        return {
            "should_trade": self.should_trade,
            "quality_score": round(self.quality_score, 4),
            "reward_risk": round(self.reward_risk, 4) if self.reward_risk is not None else None,
            "reasons": list(self.reasons),
        }


class SignalGate:
    """Evaluates a :class:`GateEvidence` into a :class:`GateVerdict`."""

    def __init__(self, config: GateConfig | None = None) -> None:
        self._config = config or GateConfig()

    def evaluate(self, evidence: GateEvidence) -> GateVerdict:
        rr = self._reward_risk(evidence)
        reasons: list[str] = []
        vetoed = False

        # ── Hard vetoes — any one of these blocks the trade outright ──────────
        if evidence.news_blackout:
            vetoed = True
            label = evidence.news_event or "high-impact event"
            reasons.append(f"VETO: {label} inside the news blackout window")

        if rr is not None and rr < self._config.min_reward_risk:
            vetoed = True
            reasons.append(
                f"VETO: reward:risk {rr:.2f} below the {self._config.min_reward_risk:.2f} floor"
            )
        elif rr is None:
            reasons.append("reward:risk undefined (missing stop or target)")

        if self._fights_strong_trend(evidence):
            vetoed = True
            reasons.append(
                f"VETO: counter-trend ({evidence.direction}) against a trending "
                f"{evidence.higher_tf_trend} higher-timeframe market"
            )

        # ── Quality score — start from the model's confidence, then adjust ────
        score = float(evidence.confidence)
        score += self._trend_adjustment(evidence, reasons)
        score += self._rr_adjustment(rr, reasons)
        score += self._divergence_adjustment(evidence, reasons)
        score += self._regime_adjustment(evidence, reasons)
        score = min(max(score, 0.0), 1.0)

        should_trade = not vetoed and score >= self._config.quality_threshold
        if not vetoed and not should_trade:
            reasons.append(
                f"quality {score:.2f} below the {self._config.quality_threshold:.2f} "
                "actionable threshold — bias only"
            )
        return GateVerdict(
            should_trade=should_trade, quality_score=score, reward_risk=rr, reasons=reasons
        )

    # ── Reward:risk ───────────────────────────────────────────────────────────

    @staticmethod
    def _reward_risk(evidence: GateEvidence) -> float | None:
        """Reward:risk to TP1 from the levels, or ``None`` if undefined.

        Risk is the entry→stop distance, reward the entry→TP1 distance, both on
        the correct side of the trade. A non-positive risk (degenerate levels)
        yields ``None`` rather than a misleading ratio.
        """
        if evidence.stop_loss is None or evidence.take_profit_1 is None:
            return None
        entry = evidence.entry
        if evidence.direction == "buy":
            risk = entry - evidence.stop_loss
            reward = evidence.take_profit_1 - entry
        else:
            risk = evidence.stop_loss - entry
            reward = entry - evidence.take_profit_1
        if risk <= 0:
            return None
        return float(reward / risk)

    # ── Veto helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _fights_strong_trend(evidence: GateEvidence) -> bool:
        """True when the bias trades *against* a trending higher-TF market.

        Only a *trending* regime triggers the veto — counter-trend plays in a
        ranging or transitional market are legitimate mean-reversion, so they are
        scored, not blocked.
        """
        if evidence.regime != "trending" or evidence.higher_tf_trend is None:
            return False
        aligned = (evidence.direction == "buy" and evidence.higher_tf_trend == "up") or (
            evidence.direction == "sell" and evidence.higher_tf_trend == "down"
        )
        return not aligned

    # ── Score adjustments (each appends its reason) ───────────────────────────

    @staticmethod
    def _trend_adjustment(evidence: GateEvidence, reasons: list[str]) -> float:
        if evidence.higher_tf_trend is None:
            return 0.0
        aligned = (evidence.direction == "buy" and evidence.higher_tf_trend == "up") or (
            evidence.direction == "sell" and evidence.higher_tf_trend == "down"
        )
        if aligned:
            reasons.append("aligned with the higher-timeframe trend")
            return _W_TREND_ALIGNED
        reasons.append("against the higher-timeframe trend")
        return _W_TREND_AGAINST

    @staticmethod
    def _rr_adjustment(rr: float | None, reasons: list[str]) -> float:
        if rr is not None and rr >= _RR_STRONG:
            reasons.append(f"clean reward:risk {rr:.2f}")
            return _W_RR_STRONG
        return 0.0

    @staticmethod
    def _divergence_adjustment(evidence: GateEvidence, reasons: list[str]) -> float:
        if evidence.rsi_divergence is None:
            return 0.0
        confirms = (evidence.direction == "buy" and evidence.rsi_divergence == "bullish") or (
            evidence.direction == "sell" and evidence.rsi_divergence == "bearish"
        )
        if confirms:
            reasons.append(f"{evidence.rsi_divergence} RSI divergence confirms the bias")
            return _W_DIVERGENCE_CONFIRMS
        reasons.append(f"{evidence.rsi_divergence} RSI divergence works against the bias")
        return _W_DIVERGENCE_CONTRADICTS

    @staticmethod
    def _regime_adjustment(evidence: GateEvidence, reasons: list[str]) -> float:
        if evidence.regime == "ranging":
            reasons.append("ranging regime — weaker directional edge")
            return _W_RANGING_REGIME
        return 0.0
