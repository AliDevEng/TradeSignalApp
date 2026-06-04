import type { IndicatorSnapshot, Signal } from "@/types/signal";

/** A complete, overridable domain Signal for component/unit tests. */
export function buildSignal(overrides: Partial<Signal> = {}): Signal {
  return {
    id: "sig-xauusd-1",
    pairId: 1,
    analysisRunId: "run-1",
    symbol: "XAUUSD",
    displayName: "Gold / US Dollar",
    direction: "buy",
    tradeStyle: "swing",
    status: "active",
    confidence: 0.84,
    entryPrice: 2368.42,
    stopLoss: 2354.8,
    stopDistancePercent: -0.00575,
    targets: [
      { label: "TP1", price: 2379.6, distancePercent: 0.00472 },
      { label: "TP2", price: 2388.9, distancePercent: 0.00865 }
    ],
    timeframe: "1h",
    generatedAt: "2026-05-08T10:35:00.000Z",
    expiresAt: "2026-05-08T16:35:00.000Z",
    riskReward: 0.82,
    rationale: "Bullish continuation above the reclaimed shelf.",
    reasoning: {
      thesis: "Continuation",
      confirmations: ["a", "b"],
      riskPlan: "manage",
      invalidation: "below shelf",
      executionNotes: ["note"]
    },
    indicators: null,
    aiProvider: "groq",
    aiModel: "llama-3.3-70b-versatile",
    outcome: "open",
    realizedR: null,
    closedAt: null,
    ...overrides
  };
}

export const sampleIndicators: IndicatorSnapshot = {
  asOf: "2026-05-08T10:00:00.000Z",
  candlesAnalyzed: 200,
  lastClose: 2367.9,
  sma20: 2361.4,
  sma50: 2352.8,
  ema20: 2362.7,
  ema50: 2354.1,
  ema200: 2338.5,
  rsi14: 63.4,
  macd: 4.21,
  macdSignal: 3.08,
  macdHistogram: 1.13,
  atr14: 6.82,
  bbUpper: 2374.2,
  bbMiddle: 2361.4,
  bbLower: 2348.6,
  bbPercent: 0.74
};
