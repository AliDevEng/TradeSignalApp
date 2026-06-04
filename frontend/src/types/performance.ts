import type { SignalTradeStyle } from "@/types/signal";

/**
 * The UI-facing track record — a normalised mirror of the backend
 * `/performance` payload (Iteration 8). All numbers are parsed to JS `number`s
 * at the mapping boundary (R figures arrive as Decimal strings on the wire);
 * `winRate`/`avgConfidence` are fractions in `[0, 1]`.
 */
export type PerformanceSummary = {
  total: number;
  wins: number;
  losses: number;
  /** Fraction in [0, 1]. */
  winRate: number;
  totalR: number;
  /** Expectancy — average realised R per signal. */
  avgR: number;
  /** Gross profit ÷ gross loss; null when there is no losing R (no finite ratio). */
  profitFactor: number | null;
  grossProfit: number;
  grossLoss: number;
};

export type CalibrationBucket = {
  /** Human band label, e.g. "60-80%". */
  label: string;
  /** Band edges as fractions in [0, 1]. */
  lower: number;
  upper: number;
  count: number;
  /** Mean stated confidence in the band — the model's prediction. */
  avgConfidence: number;
  /** Realised hit-rate in the band. */
  winRate: number;
  wins: number;
};

export type EquityPoint = {
  signalId: string;
  closedAt: string;
  realizedR: number;
  cumulativeR: number;
};

export type Performance = {
  overall: PerformanceSummary;
  /** Always carries both styles; an absent style is a zeroed summary. */
  byType: Record<SignalTradeStyle, PerformanceSummary>;
  /** Always five ordered buckets for a stable chart x-axis. */
  calibration: CalibrationBucket[];
  /** Ordered oldest-close first, ready to plot. */
  equityCurve: EquityPoint[];
  generatedAt: string;
};
