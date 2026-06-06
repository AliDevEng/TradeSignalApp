import { describe, expect, it } from "vitest";

import { notificationForEvent, parseStreamEvent, queryKeysToInvalidate } from "@/lib/stream";
import type { StreamEvent } from "@/types/stream";

describe("parseStreamEvent", () => {
  it("parses a well-formed event payload", () => {
    const raw = JSON.stringify({
      id: 7,
      type: "signal.created",
      at: "2026-06-06T10:00:00Z",
      data: { pair: "XAUUSD" }
    });
    const event = parseStreamEvent(raw);
    expect(event).not.toBeNull();
    expect(event?.id).toBe(7);
    expect(event?.type).toBe("signal.created");
    expect(event?.data.pair).toBe("XAUUSD");
  });

  it("returns null for malformed JSON", () => {
    expect(parseStreamEvent("not json")).toBeNull();
  });

  it("returns null for an unknown event type", () => {
    expect(parseStreamEvent(JSON.stringify({ type: "signal.exploded", data: {} }))).toBeNull();
  });

  it("defaults a missing data object to empty", () => {
    const event = parseStreamEvent(JSON.stringify({ type: "run.finished" }));
    expect(event?.data).toEqual({});
  });
});

describe("queryKeysToInvalidate", () => {
  it("invalidates signals + pipeline on create", () => {
    expect(queryKeysToInvalidate("signal.created")).toEqual([["signals"], ["pipeline-status"]]);
  });

  it("invalidates signals + performance on close", () => {
    expect(queryKeysToInvalidate("signal.closed")).toEqual([["signals"], ["performance"]]);
  });

  it("invalidates signals + runs + pipeline on run finished", () => {
    expect(queryKeysToInvalidate("run.finished")).toEqual([
      ["signals"],
      ["analysis-runs"],
      ["pipeline-status"]
    ]);
  });
});

function event(type: StreamEvent["type"], data: Record<string, unknown>): StreamEvent {
  return { id: 1, type, at: "2026-06-06T10:00:00Z", data };
}

describe("notificationForEvent", () => {
  it("builds a created-signal notification and marks the signal seen", () => {
    const mapped = notificationForEvent(
      event("signal.created", {
        signal_id: "abc",
        pair: "XAUUSD",
        direction: "buy",
        confidence: 0.82,
        timeframe: "1h"
      })
    );
    expect(mapped).not.toBeNull();
    expect(mapped?.tone).toBe("info");
    expect(mapped?.markSeenSignalId).toBe("abc");
    expect(mapped?.notification.id).toBe("abc");
    expect(mapped?.notification.title).toContain("BUY");
    expect(mapped?.notification.title).toContain("XAUUSD");
    expect(mapped?.notification.description).toContain("82% confidence");
    expect(mapped?.notification.href).toBe("/signals/abc");
  });

  it("tones a closed win as success and a stop as danger", () => {
    const win = notificationForEvent(
      event("signal.closed", { signal_id: "1", pair: "XAUUSD", outcome: "hit_tp1", realized_r: "1.50" })
    );
    expect(win?.tone).toBe("success");
    expect(win?.notification.id).toBe("1:closed");
    expect(win?.notification.description).toContain("1.50R");

    const loss = notificationForEvent(
      event("signal.closed", { signal_id: "2", pair: "XAUUSD", outcome: "hit_sl" })
    );
    expect(loss?.tone).toBe("danger");
    expect(loss?.markSeenSignalId).toBeUndefined();
  });

  it("does not notify for run.finished", () => {
    expect(notificationForEvent(event("run.finished", { status: "success" }))).toBeNull();
  });

  it("returns null when a signal id is missing", () => {
    expect(notificationForEvent(event("signal.created", { pair: "XAUUSD" }))).toBeNull();
  });
});
