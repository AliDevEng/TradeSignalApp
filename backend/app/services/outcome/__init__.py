"""Outcome evaluation service.

Public surface: the pure :class:`OutcomeEvaluator`, its :class:`EvaluationInput`
and :class:`OutcomeResult` value objects, and the ``EvaluatedOutcome`` literal.
The evaluator is deterministic and IO-free — it turns an open position plus the
candles since it was generated into "what happened" — so it is fully
back-testable without a database, a network, or an AI key. Persisting the result
is the outcome controller's job (Iteration 7), exactly as drafting a signal is
the AI service's job and persisting it is the analysis controller's.
"""

from __future__ import annotations

from app.services.outcome.evaluator import (
    EvaluatedOutcome,
    EvaluationInput,
    OutcomeEvaluator,
    OutcomeResult,
)

__all__ = [
    "EvaluatedOutcome",
    "EvaluationInput",
    "OutcomeEvaluator",
    "OutcomeResult",
]
