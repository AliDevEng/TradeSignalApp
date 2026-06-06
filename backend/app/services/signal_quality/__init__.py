"""Signal-quality gating — separates a directional *bias* from an *actionable* trade.

The product is always-on: every cycle emits a scalp and a swing bias. But a bias
is not a trade. This package is the deterministic layer that decides, in code (not
prompt suggestion), whether a given bias is worth acting on — scoring its quality
and raising hard vetoes for the classic ways a setup is a trap (poor reward:risk,
fighting a strong trend, a high-impact news release imminent).

Pure and side-effect free, so the policy is unit-tested directly and a signal's
``should_trade`` flag never depends on whether the model felt confident that day.
"""

from __future__ import annotations

from app.services.signal_quality.gate import (
    GateConfig,
    GateEvidence,
    GateVerdict,
    SignalGate,
)

__all__ = [
    "GateConfig",
    "GateEvidence",
    "GateVerdict",
    "SignalGate",
]
