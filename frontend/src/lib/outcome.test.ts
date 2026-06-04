import { describe, expect, it } from "vitest";

import { describeOutcome, formatR, isClosedOutcome, outcomeCategory } from "@/lib/outcome";

describe("outcomeCategory", () => {
  it("groups take-profits as wins", () => {
    expect(outcomeCategory("hit_tp1")).toBe("win");
    expect(outcomeCategory("hit_tp2")).toBe("win");
    expect(outcomeCategory("hit_tp3")).toBe("win");
  });

  it("maps stop to loss, expiry/cancel to expired, and open to open", () => {
    expect(outcomeCategory("hit_sl")).toBe("loss");
    expect(outcomeCategory("expired")).toBe("expired");
    expect(outcomeCategory("cancelled")).toBe("expired");
    expect(outcomeCategory("open")).toBe("open");
  });
});

describe("isClosedOutcome", () => {
  it("is false only for open", () => {
    expect(isClosedOutcome("open")).toBe(false);
    expect(isClosedOutcome("hit_tp2")).toBe(true);
    expect(isClosedOutcome("hit_sl")).toBe(true);
    expect(isClosedOutcome("expired")).toBe(true);
  });
});

describe("formatR", () => {
  it("signs and fixes to two decimals", () => {
    expect(formatR(2.1)).toBe("+2.10R");
    expect(formatR(-1)).toBe("-1.00R");
    expect(formatR(0)).toBe("0.00R");
  });

  it("returns null when there is no R", () => {
    expect(formatR(null)).toBeNull();
    expect(formatR(Number.NaN)).toBeNull();
  });
});

describe("describeOutcome", () => {
  it("appends R for wins and losses", () => {
    expect(describeOutcome("hit_tp2", 2.1).text).toBe("TP2 +2.10R");
    expect(describeOutcome("hit_sl", -1).text).toBe("SL -1.00R");
  });

  it("shows just the label for open, and for closed without R", () => {
    expect(describeOutcome("open", null).text).toBe("Open");
    expect(describeOutcome("expired", null).text).toBe("Expired");
    expect(describeOutcome("expired", 0.3).text).toBe("Expired +0.30R");
  });
});
