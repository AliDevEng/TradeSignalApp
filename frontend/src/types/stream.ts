/**
 * Real-time event-stream contract — the browser mirror of the backend event bus
 * (see `backend/app/services/events/bus.py::EventType`). The SSE endpoint frames
 * each event with `event: <type>` and a JSON `data` payload; these types describe
 * what the client parses back out.
 */

/** The domain events the backend publishes over `GET /api/v1/stream`. */
export const STREAM_EVENT_TYPES = ["signal.created", "signal.closed", "run.finished"] as const;

export type StreamEventType = (typeof STREAM_EVENT_TYPES)[number];

/** A parsed event off the stream. `data` is event-specific and read defensively. */
export type StreamEvent = {
  id: number;
  type: StreamEventType;
  at: string;
  data: Record<string, unknown>;
};

/** Connection state surfaced to the UI by {@link useEventStream}. */
export type StreamStatus = "connecting" | "live" | "offline";
