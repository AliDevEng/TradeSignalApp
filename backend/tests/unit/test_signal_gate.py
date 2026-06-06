"""Unit tests for the deterministic signal-quality gate.

The gate is pure, so these are a table of (evidence → verdict) cases pinning the
hard vetoes, the reward:risk maths, and the bias-vs-actionable threshold.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.signal_quality import GateConfig, GateEvidence, GateVerdict, SignalGate


def _evidence(**overrides) -> GateEvidence:
    base = {
        "direction": "buy",
        "entry": Decimal("100"),
        "stop_loss": Decimal("99"),
        "take_profit_1": Decimal("102"),  # reward:risk = 2.0
        "confidence": 0.6,
    }
    base.update(overrides)
    return GateEvidence(**base)  # type: ignore[arg-type]


def _gate(**config) -> SignalGate:
    return SignalGate(GateConfig(**config))


# ── reward:risk ───────────────────────────────────────────────────────────────


def test_reward_risk_for_a_buy():
    verdict = _gate().evaluate(_evidence())
    assert verdict.reward_risk == 2.0


def test_reward_risk_for_a_sell():
    verdict = _gate().evaluate(
        _evidence(
            direction="sell",
            entry=Decimal("100"),
            stop_loss=Decimal("101"),
            take_profit_1=Decimal("97"),  # reward 3 / risk 1
        )
    )
    assert verdict.reward_risk == 3.0


def test_reward_risk_undefined_without_levels():
    verdict = _gate().evaluate(_evidence(stop_loss=None))
    assert verdict.reward_risk is None
    assert any("undefined" in r for r in verdict.reasons)


# ── hard vetoes ───────────────────────────────────────────────────────────────


def test_poor_reward_risk_is_vetoed():
    verdict = _gate(min_reward_risk=1.5).evaluate(_evidence(take_profit_1=Decimal("100.5")))
    assert verdict.reward_risk == 0.5
    assert verdict.should_trade is False
    assert any("reward:risk" in r and "VETO" in r for r in verdict.reasons)


def test_news_blackout_is_vetoed_even_with_great_setup():
    verdict = _gate().evaluate(
        _evidence(confidence=0.95, news_blackout=True, news_event="USD CPI (high)")
    )
    assert verdict.should_trade is False
    assert any("USD CPI" in r for r in verdict.reasons)


def test_counter_trend_in_a_trending_market_is_vetoed():
    verdict = _gate().evaluate(
        _evidence(direction="buy", higher_tf_trend="down", regime="trending")
    )
    assert verdict.should_trade is False
    assert any("counter-trend" in r for r in verdict.reasons)


def test_counter_trend_in_a_ranging_market_is_allowed():
    # Mean-reversion against a directionless market is legitimate — scored, not vetoed.
    verdict = _gate().evaluate(_evidence(direction="buy", higher_tf_trend="down", regime="ranging"))
    assert not any("VETO" in r for r in verdict.reasons)


# ── quality score / threshold ─────────────────────────────────────────────────


def test_strong_aligned_setup_is_actionable():
    verdict = _gate().evaluate(
        _evidence(confidence=0.6, higher_tf_trend="up", regime="trending", rsi_divergence="bullish")
    )
    # base 0.6 + trend 0.15 + rr 0.10 + divergence 0.10 = 0.95
    assert verdict.quality_score == 0.95
    assert verdict.should_trade is True


def test_weak_setup_stays_bias_only():
    # Low confidence, no corroboration: clears the 1.5 reward:risk floor but the
    # blended quality misses the actionable bar.
    verdict = _gate(quality_threshold=0.5).evaluate(
        _evidence(confidence=0.2, take_profit_1=Decimal("101.5"))  # rr 1.5, no bonuses
    )
    assert verdict.should_trade is False
    assert any("bias only" in r for r in verdict.reasons)


def test_quality_score_is_clamped_to_unit_interval():
    verdict = _gate().evaluate(
        _evidence(confidence=1.0, higher_tf_trend="up", regime="trending", rsi_divergence="bullish")
    )
    assert verdict.quality_score == 1.0


def test_verdict_to_dict_is_json_safe():
    out = _gate().evaluate(_evidence()).to_dict()
    assert set(out) == {"should_trade", "quality_score", "reward_risk", "reasons"}
    assert isinstance(out["reasons"], list)


def test_default_config_thresholds():
    # Documented defaults — a regression guard on the conservative floor/bar.
    config = GateConfig()
    assert config.min_reward_risk == 1.5
    assert config.quality_threshold == 0.5
    assert isinstance(
        GateVerdict(should_trade=True, quality_score=0.7, reward_risk=2.0), GateVerdict
    )
