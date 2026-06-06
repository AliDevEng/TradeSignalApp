"""The outcome evaluator — a pure function from "open position + candles" to
"what happened".

This is the measurement counterpart to signal *generation*: where the AI service
drafts a trade idea, this decides — deterministically, with no IO — whether price
subsequently hit a take-profit, the stop, or aged out, and quantifies the result
in **R multiples** (profit/loss ÷ initial risk). Being pure makes it fully
back-testable: feed it historical candles and it returns the same answer every
time, no database or network required. Persisting the verdict is the outcome
controller's job, never this module's.

The touch model is a bracket order held to its full target ladder, evaluated bar
by bar oldest→newest:

* The position closes on the **first** candle whose range reaches the stop or any
  take-profit.
* **Conservative tie-break:** if a single candle's range spans *both* the stop
  and a take-profit, we cannot know which printed first, so we resolve to the
  stop (the worse outcome). This keeps the track record honest — it never claims
  a win it cannot prove.
* When a candle reaches multiple take-profits at once (a gap or a large bar), the
  **furthest** rung reached is recorded (``hit_tp3`` over ``hit_tp2``).
* If no level is touched and ``expires_at`` has lapsed, the result is marked to
  market at the last candle's close (``expired``); otherwise it stays ``open``.

``mfe``/``mae`` (max favourable/adverse excursion, in R) are tracked over the
signal's whole life, not just the candles in one fetch. The evaluator runs every
sweep against the latest fixed-size candle window, which for a multi-day swing
cannot reach back to the signal's birth; to avoid understating the excursions it
**seeds the running extremes from the signal's previously persisted ``mfe``/``mae``**
(``prior_mfe``/``prior_mae``) and then folds the current window on top. Because
``max``/``min`` are idempotent, re-folding overlapping candles across sweeps is
harmless, and an extreme reached in an earlier window survives even once it ages
out of the fetched range. (The one thing that can still be missed is a level
touched entirely during downtime longer than the candle window — inherent to any
windowed fetch, and now bounded by the *gap* rather than the signal's TTL.)

All R figures require a stop (to define risk); a signal with no stop yields
``None`` for every R-denominated field but is still classified
(``hit_tp*``/``expired``/``open``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.services.market_data.base import Candle

# The terminal vocabulary mirrors the model's ``SignalOutcome`` values, but is
# declared here as a plain ``Literal`` so the service layer stays free of the ORM
# (the same discipline by which the AI service speaks ``Literal`` directions and
# the controller maps them to the model enum).
EvaluatedOutcome = Literal[
    "open",
    "hit_tp1",
    "hit_tp2",
    "hit_tp3",
    "hit_sl",
    "expired",
    "cancelled",
]

_R_QUANTUM = Decimal("0.0001")
_TP_OUTCOMES: tuple[EvaluatedOutcome, ...] = ("hit_tp1", "hit_tp2", "hit_tp3")


def _q(value: Decimal) -> Decimal:
    """Round an R figure to the column's 4-decimal scale (Numeric(12, 4))."""
    return value.quantize(_R_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class EvaluationInput:
    """The open position to assess — plain values, never an ORM row.

    ``take_profits`` is the ordered ladder (TP1..TP3); it may hold fewer than
    three. ``stop_loss`` may be ``None`` (risk then undefined → R fields ``None``).
    """

    direction: Literal["buy", "sell"]
    entry: Decimal
    stop_loss: Decimal | None
    take_profits: Sequence[Decimal]
    generated_at: datetime
    expires_at: datetime | None
    # The signal's running excursions from the previous evaluation, in R. Seeded
    # back so extremes reached in earlier (now aged-out) candle windows are not
    # lost — the fix for understated mfe/mae on long-lived signals. ``None`` on
    # the first evaluation (or when risk is undefined), which reproduces the
    # original from-scratch behaviour.
    prior_mfe: Decimal | None = None
    prior_mae: Decimal | None = None


@dataclass(frozen=True, slots=True)
class OutcomeResult:
    """The evaluator's verdict.

    ``closed`` is ``True`` for every terminal outcome and ``False`` only for
    ``open``. ``realized_r``/``mfe``/``mae`` are ``None`` when risk is undefined;
    ``closed_at`` is the timestamp the outcome resolved (a candle's close time, or
    ``expires_at``) and ``None`` while open.
    """

    outcome: EvaluatedOutcome
    realized_r: Decimal | None
    mfe: Decimal | None
    mae: Decimal | None
    closed: bool
    closed_at: datetime | None


class OutcomeEvaluator:
    """Pure evaluator: an :class:`EvaluationInput` + candles → an :class:`OutcomeResult`."""

    def evaluate(
        self,
        signal: EvaluationInput,
        candles: Sequence[Candle],
        *,
        now: datetime,
    ) -> OutcomeResult:
        # Only candles at/after generation count; sort defensively so the
        # order-of-touch scan is correct regardless of input ordering.
        relevant = sorted(
            (c for c in candles if c.timestamp >= signal.generated_at),
            key=lambda c: c.timestamp,
        )

        is_buy = signal.direction == "buy"
        stop = signal.stop_loss
        risk = self._risk(signal.entry, stop, is_buy=is_buy)
        tps = list(signal.take_profits)

        # Running favourable/adverse price extremes, in price terms. Seeded from
        # the signal's previously persisted excursions so extremes from earlier
        # windows survive even after those candles age out of the fetched range.
        fav, adv = self._seed_extremes(
            signal.entry, signal.prior_mfe, signal.prior_mae, risk, is_buy=is_buy
        )

        for candle in relevant:
            fav, adv = self._extend_extremes(candle, fav, adv, is_buy=is_buy)

            sl_touched = stop is not None and (
                candle.low <= stop if is_buy else candle.high >= stop
            )
            tp_idx = self._furthest_tp(candle, tps, is_buy=is_buy)

            if sl_touched or tp_idx is not None:
                mfe, mae = self._excursions(signal.entry, fav, adv, risk, is_buy=is_buy)
                # Conservative tie-break: a candle spanning both resolves to SL.
                if sl_touched:
                    realized = _q(Decimal(-1)) if risk is not None else None
                    return OutcomeResult("hit_sl", realized, mfe, mae, True, candle.timestamp)
                realized = self._r_at(signal.entry, tps[tp_idx], risk, is_buy=is_buy)
                return OutcomeResult(
                    _TP_OUTCOMES[tp_idx], realized, mfe, mae, True, candle.timestamp
                )

        # No level touched.
        mfe, mae = self._excursions(signal.entry, fav, adv, risk, is_buy=is_buy)
        if signal.expires_at is not None and now >= signal.expires_at:
            realized = None
            if risk is not None and relevant:
                realized = self._r_at(signal.entry, relevant[-1].close, risk, is_buy=is_buy)
            return OutcomeResult("expired", realized, mfe, mae, True, signal.expires_at)

        return OutcomeResult("open", None, mfe, mae, False, None)

    # ── Pure helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _risk(entry: Decimal, stop: Decimal | None, *, is_buy: bool) -> Decimal | None:
        """Initial risk (entry→stop distance), or ``None`` if undefined/inconsistent.

        A stop on the wrong side of entry (non-positive distance) is treated as
        no risk rather than producing a nonsensical negative denominator.
        """
        if stop is None:
            return None
        distance = (entry - stop) if is_buy else (stop - entry)
        return distance if distance > 0 else None

    @staticmethod
    def _seed_extremes(
        entry: Decimal,
        prior_mfe: Decimal | None,
        prior_mae: Decimal | None,
        risk: Decimal | None,
        *,
        is_buy: bool,
    ) -> tuple[Decimal | None, Decimal | None]:
        """Reconstruct prior favourable/adverse *prices* from stored R excursions.

        The exact inverse of :meth:`_excursions`: for a buy ``fav = entry + mfe·risk``
        and ``adv = entry + mae·risk`` (mae ≤ 0 ⇒ below entry); for a sell the
        signs flip. Returns ``(None, None)`` when risk is undefined (then no R was
        ever stored) or on the first evaluation (no prior), so the scan starts
        from scratch exactly as before. Because the reconstruction is exact, a
        later :meth:`_excursions` over an unchanged extreme yields the same R back
        — seeding can only preserve or raise an extreme, never shrink it.
        """
        if risk is None:
            return None, None
        fav = (
            None
            if prior_mfe is None
            else (entry + prior_mfe * risk if is_buy else entry - prior_mfe * risk)
        )
        adv = (
            None
            if prior_mae is None
            else (entry + prior_mae * risk if is_buy else entry - prior_mae * risk)
        )
        return fav, adv

    @staticmethod
    def _extend_extremes(
        candle: Candle,
        fav: Decimal | None,
        adv: Decimal | None,
        *,
        is_buy: bool,
    ) -> tuple[Decimal, Decimal]:
        """Fold one candle into the running favourable/adverse price extremes."""
        if is_buy:
            new_fav = candle.high if fav is None else max(fav, candle.high)
            new_adv = candle.low if adv is None else min(adv, candle.low)
        else:
            new_fav = candle.low if fav is None else min(fav, candle.low)
            new_adv = candle.high if adv is None else max(adv, candle.high)
        return new_fav, new_adv

    @staticmethod
    def _furthest_tp(candle: Candle, tps: Sequence[Decimal], *, is_buy: bool) -> int | None:
        """Index of the furthest take-profit this candle reached, or ``None``."""
        reached: int | None = None
        for i, tp in enumerate(tps):
            if tp is None:
                continue
            touched = candle.high >= tp if is_buy else candle.low <= tp
            if touched:
                reached = i
        return reached

    @staticmethod
    def _r_at(
        entry: Decimal,
        exit_price: Decimal,
        risk: Decimal | None,
        *,
        is_buy: bool,
    ) -> Decimal | None:
        if risk is None:
            return None
        gain = (exit_price - entry) if is_buy else (entry - exit_price)
        return _q(gain / risk)

    @staticmethod
    def _excursions(
        entry: Decimal,
        fav: Decimal | None,
        adv: Decimal | None,
        risk: Decimal | None,
        *,
        is_buy: bool,
    ) -> tuple[Decimal | None, Decimal | None]:
        if risk is None or fav is None or adv is None:
            return None, None
        if is_buy:
            return _q((fav - entry) / risk), _q((adv - entry) / risk)
        return _q((entry - fav) / risk), _q((entry - adv) / risk)
