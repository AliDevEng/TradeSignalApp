import { describe, expect, it } from "vitest";

import { buildPerformanceFromSignals } from "@/lib/performance";
import { buildSignal } from "@/test/fixtures";
import type { Signal, SignalOutcome, SignalTradeStyle } from "@/types/signal";

function closed(overrides: {
  realizedR: number;
  outcome?: SignalOutcome;
  confidence?: number;
  tradeStyle?: SignalTradeStyle;
  closedAt?: string;
  id?: string;
}): Signal {
  return buildSignal({
    id: overrides.id ?? `sig-${Math.random().toString(36).slice(2)}`,
    outcome: overrides.outcome ?? (overrides.realizedR > 0 ? "hit_tp1" : "hit_sl"),
    realizedR: overrides.realizedR,
    confidence: overrides.confidence ?? 0.7,
    tradeStyle: overrides.tradeStyle ?? "swing",
    closedAt: overrides.closedAt ?? "2026-06-01T10:00:00.000Z"
  });
}

describe("buildPerformanceFromSignals", () => {
  it("ignores open and stop-less (unscored) signals", () => {
    const signals = [
      buildSignal({ id: "open", outcome: "open", realizedR: null }),
      closed({ realizedR: 2 })
    ];

    const report = buildPerformanceFromSignals(signals);

    expect(report.overall.total).toBe(1);
  });

  it("computes win-rate, totals, expectancy and profit factor", () => {
    const signals = [
      closed({ realizedR: 2 }),
      closed({ realizedR: 3 }),
      closed({ realizedR: -1 }),
      closed({ realizedR: -1 })
    ];

    const report = buildPerformanceFromSignals(signals);

    expect(report.overall.total).toBe(4);
    expect(report.overall.wins).toBe(2);
    expect(report.overall.losses).toBe(2);
    expect(report.overall.winRate).toBe(0.5);
    expect(report.overall.totalR).toBe(3);
    expect(report.overall.avgR).toBe(0.75);
    expect(report.overall.profitFactor).toBe(2.5);
  });

  it("reports a null profit factor when there are no losses", () => {
    const report = buildPerformanceFromSignals([closed({ realizedR: 2 }), closed({ realizedR: 1 })]);

    expect(report.overall.profitFactor).toBeNull();
  });

  it("splits scalp and swing", () => {
    const signals = [
      closed({ realizedR: 2, tradeStyle: "scalp" }),
      closed({ realizedR: -1, tradeStyle: "scalp" }),
      closed({ realizedR: 3, tradeStyle: "swing" })
    ];

    const report = buildPerformanceFromSignals(signals);

    expect(report.byType.scalp.total).toBe(2);
    expect(report.byType.scalp.wins).toBe(1);
    expect(report.byType.swing.total).toBe(1);
    expect(report.byType.swing.totalR).toBe(3);
  });

  it("buckets calibration by confidence with five ordered bands", () => {
    const signals = [
      closed({ realizedR: 2, confidence: 0.7 }),
      closed({ realizedR: -1, confidence: 0.7 }),
      closed({ realizedR: 1, confidence: 0.9 })
    ];

    const report = buildPerformanceFromSignals(signals);

    expect(report.calibration.map((bucket) => bucket.label)).toEqual([
      "0-20%",
      "20-40%",
      "40-60%",
      "60-80%",
      "80-100%"
    ]);
    const band = report.calibration.find((bucket) => bucket.label === "60-80%");
    expect(band?.count).toBe(2);
    expect(band?.winRate).toBe(0.5);
  });

  it("accumulates the equity curve oldest-close first", () => {
    const signals = [
      closed({ realizedR: 3, closedAt: "2026-06-03T10:00:00.000Z" }),
      closed({ realizedR: 2, closedAt: "2026-06-01T10:00:00.000Z" }),
      closed({ realizedR: -1, closedAt: "2026-06-02T10:00:00.000Z" })
    ];

    const report = buildPerformanceFromSignals(signals);

    expect(report.equityCurve.map((point) => point.cumulativeR)).toEqual([2, 1, 4]);
    expect(report.equityCurve.at(-1)?.cumulativeR).toBe(report.overall.totalR);
  });

  it("returns a zeroed report for no closed signals", () => {
    const report = buildPerformanceFromSignals([]);

    expect(report.overall.total).toBe(0);
    expect(report.overall.profitFactor).toBeNull();
    expect(report.equityCurve).toEqual([]);
    expect(report.calibration).toHaveLength(5);
  });
});
