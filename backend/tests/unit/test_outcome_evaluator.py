"""Unit tests for the pure :class:`OutcomeEvaluator`.

No database, no network — just candles in, a verdict out. These pin the rules
that make the track record trustworthy: order-of-touch, the conservative SL
tie-break, furthest-TP-wins, expiry mark-to-market, and R/excursion maths
(including the no-stop case where R is undefined).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.services.market_data.base import Candle
from app.services.outcome import EvaluationInput, OutcomeEvaluator

_GEN = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
_NOW = _GEN + timedelta(days=1)


def _candle(minute: int, *, o, h, low, c) -> Candle:
    return Candle(
        timestamp=_GEN + timedelta(minutes=minute),
        open=Decimal(str(o)),
        high=Decimal(str(h)),
        low=Decimal(str(low)),
        close=Decimal(str(c)),
    )


def _buy(stop="98", tps=("104",), expires=None) -> EvaluationInput:
    return EvaluationInput(
        direction="buy",
        entry=Decimal("100"),
        stop_loss=Decimal(stop) if stop is not None else None,
        take_profits=[Decimal(t) for t in tps],
        generated_at=_GEN,
        expires_at=expires,
    )


def _sell(stop="102", tps=("96",), expires=None) -> EvaluationInput:
    return EvaluationInput(
        direction="sell",
        entry=Decimal("100"),
        stop_loss=Decimal(stop) if stop is not None else None,
        take_profits=[Decimal(t) for t in tps],
        generated_at=_GEN,
        expires_at=expires,
    )


def _eval(signal, candles):
    return OutcomeEvaluator().evaluate(signal, candles, now=_NOW)


# ── Take-profit hits ─────────────────────────────────────────────────────────


def test_buy_hits_tp1_realises_positive_r():
    # risk = 100 - 98 = 2; tp1 = 104 → R = (104-100)/2 = 2.0
    candles = [_candle(5, o=100, h=105, low=99, c=104)]
    result = _eval(_buy(), candles)
    assert result.outcome == "hit_tp1"
    assert result.realized_r == Decimal("2.0000")
    assert result.closed is True
    assert result.closed_at == _GEN + timedelta(minutes=5)


def test_buy_records_furthest_tp_reached_in_one_candle():
    # A single large candle spans TP1..TP3 → the furthest (TP3) is recorded.
    signal = _buy(tps=("104", "108", "112"))
    candles = [_candle(5, o=100, h=113, low=100, c=112)]
    result = _eval(signal, candles)
    assert result.outcome == "hit_tp3"
    assert result.realized_r == Decimal("6.0000")  # (112-100)/2


def test_sell_hits_tp1():
    # risk = 102 - 100 = 2; tp = 96 → R = (100-96)/2 = 2.0
    candles = [_candle(5, o=100, h=101, low=95, c=96)]
    result = _eval(_sell(), candles)
    assert result.outcome == "hit_tp1"
    assert result.realized_r == Decimal("2.0000")


# ── Stop-loss + the conservative tie-break ────────────────────────────────────


def test_buy_hits_sl_is_minus_one_r():
    candles = [_candle(5, o=100, h=101, low=97, c=98)]
    result = _eval(_buy(), candles)
    assert result.outcome == "hit_sl"
    assert result.realized_r == Decimal("-1.0000")
    assert result.closed is True


def test_candle_spanning_both_resolves_to_stop():
    # low 97 ≤ stop 98 AND high 105 ≥ tp 104 in the same bar → conservative SL.
    candles = [_candle(5, o=100, h=105, low=97, c=100)]
    result = _eval(_buy(), candles)
    assert result.outcome == "hit_sl"


def test_earlier_stop_closes_before_later_tp():
    candles = [
        _candle(5, o=100, h=101, low=97, c=98),  # SL here
        _candle(10, o=98, h=106, low=98, c=105),  # TP later — must be ignored
    ]
    result = _eval(_buy(), candles)
    assert result.outcome == "hit_sl"
    assert result.closed_at == _GEN + timedelta(minutes=5)


# ── Expiry / still-open ───────────────────────────────────────────────────────


def test_no_touch_before_expiry_marks_to_market():
    # No level touched, expired → marked to market at last close (102).
    signal = _buy(tps=("110",), expires=_GEN + timedelta(hours=1))
    candles = [
        _candle(5, o=100, h=103, low=99.5, c=101),
        _candle(10, o=101, h=104, low=100, c=102),
    ]
    result = _eval(signal, candles)
    assert result.outcome == "expired"
    assert result.realized_r == Decimal("1.0000")  # (102-100)/2
    assert result.closed is True
    assert result.closed_at == signal.expires_at


def test_no_touch_not_expired_stays_open():
    signal = _buy(tps=("110",), expires=_NOW + timedelta(days=10))
    candles = [_candle(5, o=100, h=103, low=99.5, c=101)]
    result = _eval(signal, candles)
    assert result.outcome == "open"
    assert result.realized_r is None
    assert result.closed is False
    assert result.closed_at is None


# ── Excursions (MFE / MAE) ────────────────────────────────────────────────────


def test_mfe_and_mae_tracked_in_r_while_open():
    signal = _buy(tps=("110",), expires=_NOW + timedelta(days=10))
    candles = [
        _candle(5, o=100, h=103, low=99.5, c=102),
        _candle(10, o=102, h=104, low=100, c=103),
    ]
    result = _eval(signal, candles)
    # risk=2; best high 104 → MFE (104-100)/2 = 2.0; worst low 99.5 → MAE -0.25
    assert result.mfe == Decimal("2.0000")
    assert result.mae == Decimal("-0.2500")


# ── No-stop signals (R undefined) ─────────────────────────────────────────────


def test_no_stop_still_classifies_but_r_is_none():
    signal = _buy(stop=None, tps=("104",))
    candles = [_candle(5, o=100, h=105, low=99, c=104)]
    result = _eval(signal, candles)
    assert result.outcome == "hit_tp1"
    assert result.realized_r is None
    assert result.mfe is None
    assert result.mae is None


def test_no_stop_never_hits_sl():
    signal = _buy(stop=None, tps=("110",), expires=_NOW + timedelta(days=10))
    # A deep drop that would be a stop-out if a stop existed.
    candles = [_candle(5, o=100, h=101, low=80, c=85)]
    result = _eval(signal, candles)
    assert result.outcome == "open"


# ── Candle window ─────────────────────────────────────────────────────────────


def test_candles_before_generation_are_ignored():
    signal = _buy()
    candles = [
        # Before generated_at — a TP touch here must not count.
        Candle(
            timestamp=_GEN - timedelta(minutes=5),
            open=Decimal("100"),
            high=Decimal("106"),
            low=Decimal("100"),
            close=Decimal("105"),
        ),
        _candle(5, o=100, h=101, low=99.5, c=100),
    ]
    result = _eval(signal, candles)
    assert result.outcome == "open"


def test_empty_candles_open_when_not_expired():
    result = _eval(_buy(expires=_NOW + timedelta(days=10)), [])
    assert result.outcome == "open"
    assert result.mfe is None and result.mae is None
