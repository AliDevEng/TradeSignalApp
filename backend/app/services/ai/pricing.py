"""Best-effort per-model token pricing → an estimated USD cost.

Cost is *telemetry*, not a correctness concern, so this is deliberately simple
and fail-soft: an unknown model (or missing usage) yields ``None`` rather than a
wrong number or an exception. The table is published list pricing in **USD per
1,000,000 tokens** (input, output) and will drift over time — it lives in one
place so it is trivial to update, and the controller only ever sees a ``Decimal``
or ``None``.

Pure and SDK-free: it takes the provider-neutral :class:`TokenUsage`, so the
controller can compute cost without importing any provider response type.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.services.ai.base import TokenUsage

# USD per 1M tokens, (input, output). Keyed by model id; matched case-insensitively
# with a prefix fallback so versioned suffixes (e.g. a dated Claude id) still hit.
_PRICING: dict[str, tuple[Decimal, Decimal]] = {
    # Groq (Llama 3.x) — list pricing.
    "llama-3.3-70b-versatile": (Decimal("0.59"), Decimal("0.79")),
    "llama-3.1-8b-instant": (Decimal("0.05"), Decimal("0.08")),
    # Anthropic Claude.
    "claude-opus-4": (Decimal("15.00"), Decimal("75.00")),
    "claude-sonnet-4": (Decimal("3.00"), Decimal("15.00")),
    "claude-haiku-4": (Decimal("1.00"), Decimal("5.00")),
    "claude-3-5-sonnet": (Decimal("3.00"), Decimal("15.00")),
    "claude-3-5-haiku": (Decimal("0.80"), Decimal("4.00")),
}

_PER_MILLION = Decimal(1_000_000)
_COST_QUANTUM = Decimal("0.000001")  # matches the cost_usd column scale (6 dp)


def _lookup(model: str) -> tuple[Decimal, Decimal] | None:
    """Find a price for ``model``: exact match first, then longest prefix."""
    key = model.strip().lower()
    if key in _PRICING:
        return _PRICING[key]
    # Prefix match so "claude-sonnet-4-6" resolves to the "claude-sonnet-4" entry.
    candidates = [(name, price) for name, price in _PRICING.items() if key.startswith(name)]
    if not candidates:
        return None
    return max(candidates, key=lambda item: len(item[0]))[1]


def estimate_cost_usd(model: str, usage: TokenUsage | None) -> Decimal | None:
    """Estimate a call's USD cost from its token usage, or ``None`` if unknown.

    Returns ``None`` when usage is absent or the model isn't priced — a missing
    cost is honest, a fabricated one is not.
    """
    if usage is None:
        return None
    price = _lookup(model)
    if price is None:
        return None

    input_price, output_price = price
    prompt = Decimal(usage.prompt_tokens or 0)
    completion = Decimal(usage.completion_tokens or 0)
    cost = (prompt * input_price + completion * output_price) / _PER_MILLION
    return cost.quantize(_COST_QUANTUM, rounding=ROUND_HALF_UP)
