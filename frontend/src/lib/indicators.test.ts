import { describe, expect, it } from "vitest";

import { buildIndicatorGroups, describeRsi } from "@/lib/indicators";
import type { IndicatorSnapshot } from "@/types/signal";

const snapshot: IndicatorSnapshot = {
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

describe("describeRsi", () => {
  it("flags overbought above 70", () => {
    expect(describeRsi(72)).toEqual({ hint: "Overbought", tone: "bearish" });
  });

  it("flags oversold below 30", () => {
    expect(describeRsi(22)).toEqual({ hint: "Oversold", tone: "bullish" });
  });

  it("is neutral in the mid-band", () => {
    expect(describeRsi(50).tone).toBe("neutral");
  });

  it("is neutral for missing data", () => {
    expect(describeRsi(null).tone).toBe("neutral");
  });
});

describe("buildIndicatorGroups", () => {
  it("produces Momentum, Trend and Volatility groups", () => {
    const groups = buildIndicatorGroups(snapshot);
    expect(groups.map((group) => group.title)).toEqual(["Momentum", "Trend", "Volatility"]);
  });

  it("marks EMAs the price is above as bullish", () => {
    const trend = buildIndicatorGroups(snapshot).find((group) => group.title === "Trend");
    const ema200 = trend?.rows.find((row) => row.label === "EMA 200");
    expect(ema200?.tone).toBe("bullish");
  });

  it("renders an em dash for missing values", () => {
    const groups = buildIndicatorGroups({ ...snapshot, atr14: null });
    const atr = groups
      .find((group) => group.title === "Volatility")
      ?.rows.find((row) => row.label === "ATR (14)");
    expect(atr?.value).toBe("—");
  });
});
