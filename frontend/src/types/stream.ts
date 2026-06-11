/**
 * Real-time event-stream contract — the browser mirror of the backend event bus
 * (see `backend/app/services/events/bus.py::EventType`). The SSE endpoint frames
 * each event with `event: <type>` and a JSON `data` payload; these types describe
 * what the client parses back out.
 */

/** The domain events the backend publishes over `GET /api/v1/stream`. */
export const STREAM_EVENT_TYPES = [
  "signal.created",
  "signal.closed",
  "run.started",
  "run.progress",
  "run.finished"
] as const;

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

/**
 * The ordered phases a pipeline run narrates over `run.progress` — the shared
 * contract with `backend/app/controllers/analysis_controller.py::PROGRESS_PHASES`.
 * The UI renders them as a left-to-right stepper.
 */
export const PROGRESS_PHASES = ["fetching", "analyzing", "scoring", "persisting"] as const;

export type ProgressPhase = (typeof PROGRESS_PHASES)[number];

/** Short, human label per phase for the stepper. */
export const PROGRESS_PHASE_LABELS: Record<ProgressPhase, string> = {
  fetching: "Loading market data",
  analyzing: "AI analyzing",
  scoring: "Scoring setups",
  persisting: "Saving signals"
};

/**
 * A snapshot of an in-flight run, projected from the latest `run.started` /
 * `run.progress` event. Drives the live workflow stepper. `phase` is `null`
 * between `run.started` and the first `run.progress` frame (the run is live but
 * has not announced a phase yet).
 */
export type PipelineProgress = {
  runId: string;
  phase: ProgressPhase | null;
  message: string;
  pair: string | null;
  pairsTotal: number;
  pairsCompleted: number;
  /** Within the `fetching` phase: which timeframe step (1-based) of how many. */
  step: number | null;
  stepsTotal: number | null;
  /** When this snapshot was received (client clock), for staleness guards. */
  updatedAt: number;
};
