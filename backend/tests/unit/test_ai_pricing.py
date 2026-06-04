"""Unit tests for the AI cost estimator — pure, table-driven, fail-soft."""

from __future__ import annotations

from decimal import Decimal

from app.services.ai import TokenUsage, estimate_cost_usd


def test_cost_for_known_model():
    # llama-3.3-70b-versatile: 0.59 in / 0.79 out per 1M tokens.
    usage = TokenUsage(prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert estimate_cost_usd("llama-3.3-70b-versatile", usage) == Decimal("1.380000")


def test_cost_scales_with_token_counts():
    usage = TokenUsage(prompt_tokens=200, completion_tokens=100)
    # (200*0.59 + 100*0.79) / 1e6 = 0.000197
    assert estimate_cost_usd("llama-3.3-70b-versatile", usage) == Decimal("0.000197")


def test_prefix_match_resolves_versioned_model_ids():
    # A dated/versioned Claude id resolves to its base pricing entry.
    usage = TokenUsage(prompt_tokens=1_000_000, completion_tokens=0)
    assert estimate_cost_usd("claude-sonnet-4-6", usage) == Decimal("3.000000")


def test_unknown_model_is_none_not_zero():
    usage = TokenUsage(prompt_tokens=1000, completion_tokens=1000)
    assert estimate_cost_usd("some-unlisted-model", usage) is None


def test_missing_usage_is_none():
    assert estimate_cost_usd("llama-3.3-70b-versatile", None) is None


def test_partial_usage_counts_only_known_side():
    usage = TokenUsage(prompt_tokens=1_000_000, completion_tokens=None)
    assert estimate_cost_usd("llama-3.3-70b-versatile", usage) == Decimal("0.590000")
