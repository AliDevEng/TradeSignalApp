import { describe, expect, it } from "vitest";

import {
  formatIndicator,
  formatRelativeTime,
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
