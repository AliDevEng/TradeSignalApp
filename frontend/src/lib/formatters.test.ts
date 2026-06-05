import { describe, expect, it } from "vitest";

import {
  formatCountdown,
  formatIndicator,
  formatRelativeTime,
  formatRiskReward,
  formatSignedPercent,
  getPricePrecision
} from "@/lib/formatters";

describe("getPricePrecision", () => {
  it("uses 2 decimals for gold", () => {
    expect(getPricePrecision("XAUUSD")).toBe(2);
  });

  it("uses 3 decimals for JPY pairs", () => {
    expect(getPricePrecision("USDJPY")).toBe(3);
  });

  it("defaults to 5 decimals for other FX pairs", () => {
    expect(getPricePrecision("EURUSD")).toBe(5);
  });
});

describe("formatSignedPercent", () => {
  it("prefixes a plus sign for gains", () => {
    expect(formatSignedPercent(0.0123)).toBe("+1.23%");
  });

  it("keeps the minus sign for losses", () => {
    expect(formatSignedPercent(-0.04)).toBe("-4.00%");
  });

  it("does not prefix a sign for zero", () => {
    expect(formatSignedPercent(0)).toBe("0.00%");
  });
});

describe("formatIndicator", () => {
  it("uses coarse precision for large magnitudes", () => {
    expect(formatIndicator(2361.4)).toBe("2,361.40");
  });

  it("uses fine precision for sub-unit FX values", () => {
    expect(formatIndicator(1.0836)).toBe("1.08360");
  });
});

describe("formatRiskReward", () => {
  it("drops the decimal when the ratio rounds to a whole number", () => {
    expect(formatRiskReward(2.04)).toBe("2");
    expect(formatRiskReward(2.02)).toBe("2");
    expect(formatRiskReward(2)).toBe("2");
  });

  it("keeps a single decimal when meaningful", () => {
    expect(formatRiskReward(2.1)).toBe("2.1");
    expect(formatRiskReward(2.15)).toBe("2.2");
    expect(formatRiskReward(0.82)).toBe("0.8");
  });
});

describe("formatCountdown", () => {
  it("formats minutes and seconds", () => {
    expect(formatCountdown(12 * 60_000 + 30_000)).toBe("12m 30s");
  });

  it("formats sub-minute durations as seconds only", () => {
    expect(formatCountdown(45_000)).toBe("45s");
  });

  it("formats long cadences with hours", () => {
    expect(formatCountdown(60 * 60_000 + 5 * 60_000)).toBe("1h 5m");
  });

  it("collapses elapsed or invalid durations", () => {
    expect(formatCountdown(0)).toBe("any moment now");
    expect(formatCountdown(-1_000)).toBe("any moment now");
    expect(formatCountdown(Number.NaN)).toBe("any moment now");
  });
});

describe("formatRelativeTime", () => {
  const now = Date.parse("2026-06-02T12:00:00.000Z");

  it("describes a recent past time", () => {
    expect(formatRelativeTime(now - 45_000, now)).toBe("45 seconds ago");
  });

  it("describes a future time", () => {
    expect(formatRelativeTime(now + 2 * 60 * 60 * 1000, now)).toBe("in 2 hours");
  });

  it("falls back to 'unknown' for an unparseable value", () => {
    expect(formatRelativeTime("not-a-date", now)).toBe("unknown");
  });
});
