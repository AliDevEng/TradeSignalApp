import { describe, expect, it } from "vitest";

import { filterSignals, refineSignals, sortSignals } from "@/lib/signalFilters";
import { signals } from "@/lib/mockSignals";
import type { SignalRefinement } from "@/lib/signalFilters";

const base: SignalRefinement = {
  direction: "all",
  tradeStyle: "all",
  status: "all",
  outcome: "all",
  pair: "all",
  sort: "confidence"
};

describe("filterSignals", () => {
  it("filters by direction", () => {
    const result = filterSignals(signals, { ...base, direction: "buy" });
    expect(result.every((signal) => signal.direction === "buy")).toBe(true);
    expect(result.length).toBeGreaterThan(0);
  });

  it("filters by status", () => {
    const result = filterSignals(signals, { ...base, status: "active" });
    expect(result.every((signal) => signal.status === "active")).toBe(true);
  });

  it("filters by pair symbol", () => {
    const result = filterSignals(signals, { ...base, pair: "EURUSD" });
    expect(result.every((signal) => signal.symbol === "EURUSD")).toBe(true);
  });

  it("filters by trade style", () => {
    const result = filterSignals(signals, { ...base, tradeStyle: "scalp" });
    expect(result.every((signal) => signal.tradeStyle === "scalp")).toBe(true);
    expect(result.length).toBeGreaterThan(0);
  });

  it("filters by outcome category (wins)", () => {
    const result = filterSignals(signals, { ...base, outcome: "win" });
    expect(result.every((signal) => signal.outcome.startsWith("hit_tp"))).toBe(true);
    expect(result.length).toBeGreaterThan(0);
  });

  it("filters by outcome category (losses)", () => {
    const result = filterSignals(signals, { ...base, outcome: "loss" });
    expect(result.every((signal) => signal.outcome === "hit_sl")).toBe(true);
  });

  it("filters by outcome category (open)", () => {
    const result = filterSignals(signals, { ...base, outcome: "open" });
    expect(result.every((signal) => signal.outcome === "open")).toBe(true);
  });
});

describe("sortSignals", () => {
  it("sorts by confidence descending", () => {
    const result = sortSignals(signals, "confidence");
    for (let i = 1; i < result.length; i += 1) {
      expect(result[i - 1]!.confidence).toBeGreaterThanOrEqual(result[i]!.confidence);
    }
  });

  it("sorts by symbol alphabetically", () => {
    const result = sortSignals(signals, "symbol");
    const symbols = result.map((signal) => signal.symbol);
    expect(symbols).toEqual([...symbols].sort((a, b) => a.localeCompare(b)));
  });

  it("does not mutate the input array", () => {
    const snapshot = [...signals];
    sortSignals(signals, "newest");
    expect(signals).toEqual(snapshot);
  });
});

describe("refineSignals", () => {
  it("filters then sorts", () => {
    const result = refineSignals(signals, { ...base, direction: "buy", sort: "newest" });
    expect(result.every((signal) => signal.direction === "buy")).toBe(true);
    for (let i = 1; i < result.length; i += 1) {
      const prev = new Date(result[i - 1]!.generatedAt).getTime();
      const curr = new Date(result[i]!.generatedAt).getTime();
      expect(prev).toBeGreaterThanOrEqual(curr);
    }
  });
});
