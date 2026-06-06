import { describe, expect, it } from "vitest";

import {
  eventKey,
  groupEventsByDay,
  impactTone,
  isHighImpact,
  nextHighImpactEvent
} from "@/lib/calendar";
import type { EconomicEvent } from "@/types/calendar";

const NOW = new Date("2026-06-07T10:00:00Z").getTime();

function event(overrides: Partial<EconomicEvent> = {}): EconomicEvent {
  return {
    title: "US CPI",
    currency: "USD",
    impact: "high",
    scheduledAt: new Date(NOW + 2 * 3_600_000).toISOString(),
    ...overrides
  };
}

describe("calendar helpers", () => {
  it("builds a stable, distinguishing event key", () => {
    expect(eventKey(event())).toContain("USD");
    expect(eventKey(event())).toContain("US CPI");
    expect(eventKey(event({ title: "NFP" }))).not.toBe(eventKey(event()));
  });

  it("classifies impact case-insensitively", () => {
    expect(isHighImpact(event({ impact: "HIGH" }))).toBe(true);
    expect(isHighImpact(event({ impact: "medium" }))).toBe(false);
  });

  it("maps impact to a tone", () => {
    expect(impactTone(event({ impact: "high" }))).toBe("danger");
    expect(impactTone(event({ impact: "medium" }))).toBe("gold");
    expect(impactTone(event({ impact: "low" }))).toBe("muted");
  });

  describe("nextHighImpactEvent", () => {
    it("returns the soonest upcoming high-impact event", () => {
      const soon = event({ title: "CPI", scheduledAt: new Date(NOW + 3_600_000).toISOString() });
      const later = event({ title: "FOMC", scheduledAt: new Date(NOW + 5 * 3_600_000).toISOString() });
      expect(nextHighImpactEvent([later, soon], NOW)?.title).toBe("CPI");
    });

    it("ignores past events and non-high impact", () => {
      const past = event({ scheduledAt: new Date(NOW - 3_600_000).toISOString() });
      const medium = event({ impact: "medium" });
      expect(nextHighImpactEvent([past, medium], NOW)).toBeNull();
    });
  });

  describe("groupEventsByDay", () => {
    it("groups upcoming events by day with Today/Tomorrow labels", () => {
      const today = event({ scheduledAt: new Date(NOW + 3_600_000).toISOString() });
      const tomorrow = event({ scheduledAt: new Date(NOW + 26 * 3_600_000).toISOString() });
      const groups = groupEventsByDay([tomorrow, today], NOW);

      expect(groups).toHaveLength(2);
      expect(groups[0].label).toBe("Today");
      expect(groups[1].label).toBe("Tomorrow");
    });

    it("drops events already in the past", () => {
      const past = event({ scheduledAt: new Date(NOW - 3_600_000).toISOString() });
      expect(groupEventsByDay([past], NOW)).toHaveLength(0);
    });
  });
});
