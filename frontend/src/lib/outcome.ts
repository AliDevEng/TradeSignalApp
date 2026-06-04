import type { SignalOutcome } from "@/types/signal";

/**
 * Outcome presentation + filtering helpers. Pure and UI-agnostic so they are
 * trivially testable and shared by the badge, the filters, and the level map.
 *
 * The backend outcome enum is fine-grained (`hit_tp1`/`hit_tp2`/`hit_tp3`/…),
 * but for filtering and colour the UI groups it into four **categories**:
 * `open`, `win` (any take-profit), `loss` (stop), and `expired` (expired or
 * cancelled — a non-result that never resolved to a TP/SL).
 */
export type OutcomeCategory = "open" | "win" | "loss" | "expired";

const WIN_OUTCOMES = new Set<SignalOutcome>(["hit_tp1", "hit_tp2", "hit_tp3"]);

const OUTCOME_LABELS: Record<SignalOutcome, string> = {
  open: "Open",
  hit_tp1: "TP1",
  hit_tp2: "TP2",
  hit_tp3: "TP3",
  hit_sl: "SL",
  expired: "Expired",
  cancelled: "Cancelled"
};

export function outcomeCategory(outcome: SignalOutcome): OutcomeCategory {
  if (WIN_OUTCOMES.has(outcome)) {
    return "win";
  }
  if (outcome === "hit_sl") {
    return "loss";
  }
  if (outcome === "expired" || outcome === "cancelled") {
    return "expired";
  }
  return "open";
}

/** A signal is "closed" once it has reached any terminal outcome. */
export function isClosedOutcome(outcome: SignalOutcome): boolean {
  return outcome !== "open";
}

/** Realised R as a signed, 2-dp label: 2.1 → "+2.10R", -1 → "-1.00R". */
export function formatR(realizedR: number | null): string | null {
  if (realizedR === null || !Number.isFinite(realizedR)) {
    return null;
  }

  const sign = realizedR > 0 ? "+" : realizedR < 0 ? "-" : "";
  return `${sign}${Math.abs(realizedR).toFixed(2)}R`;
}

export type OutcomeDescriptor = {
  category: OutcomeCategory;
  /** Short status word, e.g. "TP2", "SL", "Expired", "Open". */
  label: string;
  /** Result label including R when available, e.g. "TP2 +2.10R", "SL -1.00R". */
  text: string;
};

/**
 * Describe an outcome for display: its category, a short label, and a combined
 * text that appends the realised R when there is one (wins/losses always have
 * one; an expired signal may, if it was marked to market against a stop).
 */
export function describeOutcome(
  outcome: SignalOutcome,
  realizedR: number | null
): OutcomeDescriptor {
  const category = outcomeCategory(outcome);
  const label = OUTCOME_LABELS[outcome];
  const r = formatR(realizedR);
  const text = category === "open" || r === null ? label : `${label} ${r}`;

  return { category, label, text };
}
