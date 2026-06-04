import { describe, expect, it } from "vitest";

import { mapApiPerformance } from "@/lib/performanceMappers";
import type { ApiPerformance } from "@/types/tradeApi";

function buildApiPerformance(overrides: Partial<ApiPerformance> = {}): ApiPerformance {
  const emptySummary = {
    total: 0,
    wins: 0,
    losses: 0,
    win_rate: 0,
    total_r: "0",
    avg_r: "0",
    profit_factor: null,
    gross_profit: "0",
    gross_loss: "0"
  };

  return {
    overall: {
      total: 4,
      wins: 3,
      losses: 1,
      win_rate: 0.75,
      total_r: "4.5000",
      avg_r: "1.1250",
      profit_factor: 5.5,
      gross_profit: "5.5000",
      gross_loss: "1.0000"
    },
    by_type: { scalp: { ...emptySummary }, swing: { ...emptySummary } },
    calibration: [
      {
        label: "80-100%",
        lower: 0.8,
        upper: 1,
        count: 2,
        avg_confidence: 0.85,
        win_rate: 1,
        wins: 2
      }
    ],
    equity_curve: [
      { signal_id: "s1", closed_at: "2026-06-01T10:00:00Z", realized_r: "2.5000", cumulative_r: "2.5000" }
    ],
    generated_at: "2026-06-04T09:00:00Z",
    ...overrides
  };
}

describe("mapApiPerformance", () => {
  it("parses Decimal-string R fields to numbers", () => {
    const result = mapApiPerformance(buildApiPerformance());

    expect(result.overall.totalR).toBe(4.5);
    expect(result.overall.avgR).toBe(1.125);
    expect(result.overall.grossProfit).toBe(5.5);
    expect(result.equityCurve[0].realizedR).toBe(2.5);
    expect(result.equityCurve[0].cumulativeR).toBe(2.5);
  });

  it("keeps ratio fields and counts as numbers", () => {
    const result = mapApiPerformance(buildApiPerformance());

    expect(result.overall.winRate).toBe(0.75);
    expect(result.overall.profitFactor).toBe(5.5);
    expect(result.overall.wins).toBe(3);
  });

  it("preserves a null profit factor instead of coercing it to zero", () => {
    const api = buildApiPerformance();
    api.overall.profit_factor = null;

    const result = mapApiPerformance(api);

    expect(result.overall.profitFactor).toBeNull();
  });

  it("maps both style summaries and the calibration buckets", () => {
    const result = mapApiPerformance(buildApiPerformance());

    expect(Object.keys(result.byType).sort()).toEqual(["scalp", "swing"]);
    expect(result.calibration[0].label).toBe("80-100%");
    expect(result.calibration[0].avgConfidence).toBe(0.85);
  });

  it("defaults unparseable money strings to zero", () => {
    const api = buildApiPerformance();
    api.overall.total_r = "not-a-number";

    const result = mapApiPerformance(api);

    expect(result.overall.totalR).toBe(0);
  });
});
