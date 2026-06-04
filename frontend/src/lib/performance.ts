import type { Signal, SignalTradeStyle } from "@/types/signal";
import type {
  CalibrationBucket,
  EquityPoint,
  Performance,
  PerformanceSummary
} from "@/types/performance";

/**
 * Client-side track-record aggregation, mirroring the backend
 * `PerformanceCalculator` (services/performance/calculator.py). It exists for the
 * **offline preview fallback** only — when the live API is unreachable the
 * Performance dashboard derives a track record from the bundled mock signals so
 * the page still demonstrates its shape. In normal operation the page consumes
 * the backend's aggregation verbatim.
 *
 * A signal is scored only once it is **closed with a defined R** (`realizedR`
 * non-null); a "win" is `realizedR > 0`. Both rules match the backend so the
 * preview behaves like production.
 */

const STYLES: SignalTradeStyle[] = ["scalp", "swing"];
const BUCKET_COUNT = 5;
const BUCKET_WIDTH = 1 / BUCKET_COUNT;

type ScoredSignal = {
  signalId: string;
  style: SignalTradeStyle;
  confidence: number;
  realizedR: number;
  closedAt: string;
};

function round4(value: number): number {
  return Math.round(value * 10_000) / 10_000;
}

function toScored(signals: Signal[]): ScoredSignal[] {
  return signals
    .filter((signal) => signal.outcome !== "open" && signal.realizedR !== null)
    .map((signal) => ({
      signalId: signal.id,
      style: signal.tradeStyle,
      confidence: signal.confidence,
      realizedR: signal.realizedR as number,
      closedAt: signal.closedAt ?? signal.generatedAt
    }))
    .sort((first, second) => new Date(first.closedAt).getTime() - new Date(second.closedAt).getTime());
}

function summarise(signals: ScoredSignal[]): PerformanceSummary {
  const total = signals.length;
  if (total === 0) {
    return {
      total: 0,
      wins: 0,
      losses: 0,
      winRate: 0,
      totalR: 0,
      avgR: 0,
      profitFactor: null,
      grossProfit: 0,
      grossLoss: 0
    };
  }

  let wins = 0;
  let grossProfit = 0;
  let grossLoss = 0;
  let totalR = 0;

  for (const signal of signals) {
    totalR += signal.realizedR;
    if (signal.realizedR > 0) {
      wins += 1;
      grossProfit += signal.realizedR;
    } else if (signal.realizedR < 0) {
      grossLoss += -signal.realizedR;
    }
  }

  return {
    total,
    wins,
    losses: total - wins,
    winRate: wins / total,
    totalR: round4(totalR),
    avgR: round4(totalR / total),
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : null,
    grossProfit: round4(grossProfit),
    grossLoss: round4(grossLoss)
  };
}

function bucketIndex(confidence: number): number {
  return Math.min(Math.max(Math.floor(confidence * BUCKET_COUNT), 0), BUCKET_COUNT - 1);
}

function calibrate(signals: ScoredSignal[]): CalibrationBucket[] {
  const buckets: ScoredSignal[][] = Array.from({ length: BUCKET_COUNT }, () => []);
  for (const signal of signals) {
    buckets[bucketIndex(signal.confidence)].push(signal);
  }

  return buckets.map((members, index) => {
    const lower = index * BUCKET_WIDTH;
    const upper = (index + 1) * BUCKET_WIDTH;
    const count = members.length;
    const wins = members.filter((signal) => signal.realizedR > 0).length;

    return {
      label: `${Math.round(lower * 100)}-${Math.round(upper * 100)}%`,
      lower,
      upper,
      count,
      avgConfidence:
        count > 0 ? members.reduce((sum, signal) => sum + signal.confidence, 0) / count : 0,
      winRate: count > 0 ? wins / count : 0,
      wins
    };
  });
}

function equityCurve(signals: ScoredSignal[]): EquityPoint[] {
  let running = 0;
  return signals.map((signal) => {
    running += signal.realizedR;
    return {
      signalId: signal.signalId,
      closedAt: signal.closedAt,
      realizedR: round4(signal.realizedR),
      cumulativeR: round4(running)
    };
  });
}

/** Build a full {@link Performance} report from domain signals (preview only). */
export function buildPerformanceFromSignals(
  signals: Signal[],
  now: string = new Date().toISOString()
): Performance {
  const scored = toScored(signals);

  return {
    overall: summarise(scored),
    byType: Object.fromEntries(
      STYLES.map((style) => [style, summarise(scored.filter((signal) => signal.style === style))])
    ) as Record<SignalTradeStyle, PerformanceSummary>,
    calibration: calibrate(scored),
    equityCurve: equityCurve(scored),
    generatedAt: now
  };
}
