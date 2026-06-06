import { describe, expect, it } from "vitest";

import {
  notificationForEvent,
  parseStreamEvent,
  queryKeysToInvalidate,
  shouldSurfaceEvent,
  type SurfacePrefs
} from "@/lib/stream";
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

describe("shouldSurfaceEvent", () => {
  const prefs: SurfacePrefs = {
    enabled: true,
    minConfidence: 0.7,
    styles: ["scalp", "swing"],
    onlyActionable: true,
    onSignalCreated: true,
    onSignalClosed: true
  };

  it("suppresses everything when notifications are disabled", () => {
    expect(
      shouldSurfaceEvent(event("signal.created", { confidence: 0.9, should_trade: true }), {
        ...prefs,
        enabled: false
      })
    ).toBe(false);
  });

  it("admits an actionable, confident, in-style new signal", () => {
    expect(
      shouldSurfaceEvent(
        event("signal.created", { confidence: 0.8, should_trade: true, signal_type: "scalp" }),
        prefs
      )
    ).toBe(true);
  });

  it("filters out a signal below the minimum confidence", () => {
    expect(
      shouldSurfaceEvent(event("signal.created", { confidence: 0.5, should_trade: true }), prefs)
    ).toBe(false);
  });

  it("filters out a non-actionable signal when only-actionable is set", () => {
    expect(
      shouldSurfaceEvent(event("signal.created", { confidence: 0.9, should_trade: false }), prefs)
    ).toBe(false);
  });

  it("admits a non-actionable signal when only-actionable is off", () => {
    expect(
      shouldSurfaceEvent(event("signal.created", { confidence: 0.9, should_trade: false }), {
        ...prefs,
        onlyActionable: false
      })
    ).toBe(true);
  });

  it("filters out a muted style", () => {
    expect(
      shouldSurfaceEvent(
        event("signal.created", { confidence: 0.9, should_trade: true, signal_type: "swing" }),
        { ...prefs, styles: ["scalp"] }
      )
    ).toBe(false);
  });

  it("respects the per-event close toggle", () => {
    const closed = event("signal.closed", { signal_type: "scalp", outcome: "hit_tp1" });
    expect(shouldSurfaceEvent(closed, prefs)).toBe(true);
    expect(shouldSurfaceEvent(closed, { ...prefs, onSignalClosed: false })).toBe(false);
  });

  it("never surfaces run.finished", () => {
    expect(shouldSurfaceEvent(event("run.finished", { status: "success" }), prefs)).toBe(false);
  });

  it("fails open on confidence when the payload omits it", () => {
    expect(
      shouldSurfaceEvent(event("signal.created", { should_trade: true }), prefs)
    ).toBe(true);
  });
});
