/**
 * Pure helpers for the real-time stream — parsing, query invalidation, and
 * event→notification mapping. Kept free of React/EventSource so the mapping
 * logic is unit-tested directly; {@link useEventStream} wires these to the
 * browser's EventSource and the query client.
 */

import type { AppNotification } from "@/store/notificationStore";
import type { ToastTone } from "@/store/toastStore";
import { STREAM_EVENT_TYPES, type StreamEvent, type StreamEventType } from "@/types/stream";

const EVENT_TYPES = new Set<string>(STREAM_EVENT_TYPES);

function isStreamEventType(value: unknown): value is StreamEventType {
  return typeof value === "string" && EVENT_TYPES.has(value);
}

/**
 * Parse a raw SSE `data` payload into a {@link StreamEvent}, or `null` if it is
 * malformed or of an unknown type. Total and defensive — a single bad frame must
 * never throw and break the stream consumer.
 */
export function parseStreamEvent(raw: string): StreamEvent | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof parsed !== "object" || parsed === null) {
    return null;
  }
  const record = parsed as Record<string, unknown>;
  if (!isStreamEventType(record.type)) {
    return null;
  }
  const data = typeof record.data === "object" && record.data !== null
    ? (record.data as Record<string, unknown>)
    : {};
  return {
    id: typeof record.id === "number" ? record.id : 0,
    type: record.type,
    at: typeof record.at === "string" ? record.at : new Date().toISOString(),
    data
  };
}

/**
 * The React-Query key prefixes to invalidate for an event, so the UI refetches
 * the affected views the instant something changes server-side. Prefixes match
 * `tradeQueryKeys` by React-Query's partial-match semantics.
 */
export function queryKeysToInvalidate(type: StreamEventType): string[][] {
  switch (type) {
    case "signal.created":
      return [["signals"], ["pipeline-status"]];
    case "signal.closed":
      return [["signals"], ["performance"]];
    case "run.finished":
      return [["signals"], ["analysis-runs"], ["pipeline-status"]];
    default:
      return [];
  }
}

export type StreamNotification = {
  notification: AppNotification;
  tone: ToastTone;
  /**
   * When set, the signal id to also mark "seen" so the polling notifier
   * (NotificationBell) does not re-announce a signal the stream already did.
   */
  markSeenSignalId?: string;
};

const WIN_OUTCOMES = new Set(["hit_tp1", "hit_tp2", "hit_tp3"]);

function str(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

/**
 * Map an event to a user-facing notification, or `null` when it should not raise
 * one (e.g. `run.finished`, which only refreshes views). Pure and defensive
 * against a partial payload.
 */
export function notificationForEvent(event: StreamEvent): StreamNotification | null {
  const data = event.data;
  if (event.type === "signal.created") {
    const signalId = str(data.signal_id);
    if (!signalId) {
      return null;
    }
    const direction = str(data.direction, "new").toUpperCase();
    const pair = str(data.pair, "—");
    const confidence = typeof data.confidence === "number" ? Math.round(data.confidence * 100) : null;
    const timeframe = str(data.timeframe).toUpperCase();
    const descriptionParts = [
      confidence !== null ? `${confidence}% confidence` : null,
      timeframe ? `on ${timeframe}` : null
    ].filter(Boolean);
    return {
      notification: {
        id: signalId,
        title: `New ${direction} signal · ${pair}`,
        description: descriptionParts.join(" ") || "A new trade signal is available.",
        href: `/signals/${signalId}`,
        createdAt: event.at,
        read: false
      },
      tone: "info",
      markSeenSignalId: signalId
    };
  }

  if (event.type === "signal.closed") {
    const signalId = str(data.signal_id);
    if (!signalId) {
      return null;
    }
    const pair = str(data.pair, "—");
    const outcome = str(data.outcome, "closed");
    const realizedR = str(data.realized_r);
    const outcomeLabel = outcome.replace(/_/g, " ").toUpperCase();
    return {
      notification: {
        id: `${signalId}:closed`,
        title: `Signal closed · ${pair}`,
        description: realizedR ? `${outcomeLabel} (${realizedR}R)` : outcomeLabel,
        href: `/signals/${signalId}`,
        createdAt: event.at,
        read: false
      },
      tone: WIN_OUTCOMES.has(outcome) ? "success" : outcome === "hit_sl" ? "danger" : "info"
    };
  }

  return null;
}
