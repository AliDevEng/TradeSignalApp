import { describe, expect, it } from "vitest";

import {
  getIndicatorReferenceLevels,
  getPrimaryTarget,
  getSignalPriceLevels
} from "@/lib/trading";
import type { IndicatorSnapshot, Signal } from "@/types/signal";

const signal: Signal = {
  id: "sig-1",
  pairId: 1,
  analysisRunId: "run-1",
  symbol: "XAUUSD",
  displayName: "Gold / US Dollar",
  direction: "buy",
  tradeStyle: "swing",
  status: "active",
  confidence: 0.8,
  entryPrice: 2368.42,
  stopLoss: 2354.8,
  stopDistancePercent: -0.00575,
  targets: [
    { label: "TP1", price: 2379.6, distancePercent: 0.0047 },
    { label: "TP2", price: 2388.9, distancePercent: 0.0086 }
  ],
  timeframe: "1h",
  generatedAt: "2026-05-08T10:35:00.000Z",
  expiresAt: null,
  riskReward: 0.82,
  rationale: "x",
  reasoning: {
    thesis: "",
    confirmations: [],
    riskPlan: "",
    invalidation: "",
    executionNotes: []
  },
  indicators: null,
  aiProvider: null,
  aiModel: null
};

describe("getPrimaryTarget", () => {
  it("returns the first target price", () => {
    expect(getPrimaryTarget(signal)).toBe(2379.6);
  });

  it("returns null when there are no targets", () => {
    expect(getPrimaryTarget({ ...signal, targets: [] })).toBeNull();
  });
});

describe("getSignalPriceLevels", () => {
  it("orders entry, stop, then targets", () => {
    const levels = getSignalPriceLevels(signal);
    expect(levels.map((level) => level.tone)).toEqual(["entry", "stop", "target", "target"]);
  });

  it("omits the stop level when there is no stop loss", () => {
    const levels = getSignalPriceLevels({ ...signal, stopLoss: null, stopDistancePercent: null });
    expect(levels.some((level) => level.tone === "stop")).toBe(false);
  });
});

describe("getIndicatorReferenceLevels", () => {
  const indicators: IndicatorSnapshot = {
    asOf: null,
    candlesAnalyzed: 0,
    lastClose: null,
    sma20: null,
    sma50: null,
    ema20: 2362.7,
    ema50: null,
    ema200: 2338.5,
    rsi14: null,
    macd: null,
    macdSignal: null,
    macdHistogram: null,
    atr14: null,
    bbUpper: 2374.2,
    bbMiddle: null,
    bbLower: 2348.6,
    bbPercent: null
  };

  it("returns only the populated reference levels", () => {
    const refs = getIndicatorReferenceLevels("sig-1", indicators);
    expect(refs.map((ref) => ref.label)).toEqual(["BB Upper", "EMA20", "EMA200", "BB Lower"]);
  });

  it("returns nothing when there is no snapshot", () => {
    expect(getIndicatorReferenceLevels("sig-1", null)).toEqual([]);
  });
});
