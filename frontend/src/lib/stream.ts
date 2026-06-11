/**
 * Pure helpers for the real-time stream — parsing, query invalidation, and
 * event→notification mapping. Kept free of React/EventSource so the mapping
 * logic is unit-tested directly; {@link useEventStream} wires these to the
 * browser's EventSource and the query client.
 */

import type { AppNotification } from "@/store/notificationStore";
import type { ToastTone } from "@/store/toastStore";
import {
  PROGRESS_PHASES,
  STREAM_EVENT_TYPES,
  type PipelineProgress,
  type ProgressPhase,
  type StreamEvent,
  type StreamEventType
} from "@/types/stream";

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
    // A run starting flips the polled status to "running" immediately rather than
    // waiting for the next poll, so the banner reacts the instant a cycle begins.
    case "run.started":
      return [["pipeline-status"]];
    case "run.finished":
      return [["signals"], ["analysis-runs"], ["pipeline-status"]];
    // `run.progress` is purely store-driven (no query owns the phase), so it
    // triggers no refetch — the live stepper reads the progress store directly.
    default:
      return [];
  }
}

const PHASE_SET = new Set<string>(PROGRESS_PHASES);

function num(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function optionalStr(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

/**
 * Project a `run.started` / `run.progress` event into a {@link PipelineProgress}
 * snapshot for the progress store, or `null` for any other event (or a frame with
 * no run id). Pure and defensive against a partial payload, so a single odd frame
 * can never break the live stepper.
 */
export function progressFromEvent(event: StreamEvent): PipelineProgress | null {
  if (event.type !== "run.started" && event.type !== "run.progress") {
    return null;
  }
  const data = event.data;
  const runId = optionalStr(data.run_id);
  if (!runId) {
    return null;
  }
  const rawPhase = data.phase;
  const phase: ProgressPhase | null =
    typeof rawPhase === "string" && PHASE_SET.has(rawPhase) ? (rawPhase as ProgressPhase) : null;
  return {
    runId,
    phase,
    message: str(data.message, event.type === "run.started" ? "Starting analysis…" : ""),
    pair: optionalStr(data.pair),
    pairsTotal: num(data.pairs_total, 0),
    pairsCompleted: num(data.pairs_completed, 0),
    step: typeof data.step === "number" ? data.step : null,
    stepsTotal: typeof data.steps_total === "number" ? data.steps_total : null,
    updatedAt: Date.now()
  };
}

/**
 * The client-side surfacing policy — a pure mirror of the backend's
 * `NotificationPreferences.should_notify` (see
 * `backend/app/services/notifications/preferences.py`). It decides whether a
 * stream event should raise an in-app toast + feed entry in *this* browser; it
 * never affects cache invalidation, which always runs so views stay fresh.
 */
export type SurfacePrefs = {
  enabled: boolean;
  minConfidence: number;
  styles: string[];
  onlyActionable: boolean;
  onSignalCreated: boolean;
  onSignalClosed: boolean;
};

function styleAllowed(data: Record<string, unknown>, styles: string[]): boolean {
  // Empty list = no style filter. A payload with no style is allowed through
  // rather than silently dropped (matches the backend).
  if (styles.length === 0) {
    return true;
  }
  const style = data.signal_type;
  return typeof style !== "string" || styles.includes(style);
}

export function shouldSurfaceEvent(event: StreamEvent, prefs: SurfacePrefs): boolean {
  if (!prefs.enabled) {
    return false;
  }
  const data = event.data;
  if (event.type === "signal.created") {
    if (!prefs.onSignalCreated || !styleAllowed(data, prefs.styles)) {
      return false;
    }
    if (prefs.onlyActionable && data.should_trade === false) {
      return false;
    }
    // No confidence on the payload → don't gate on it (fail open for the flag).
    return typeof data.confidence === "number" ? data.confidence >= prefs.minConfidence : true;
  }
  if (event.type === "signal.closed") {
    return prefs.onSignalClosed && styleAllowed(data, prefs.styles);
  }
  return false;
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
