/**
 * Lightweight, pluggable analytics seam. Events are queued through a single
 * `track` function so the rest of the app never depends on a concrete provider;
 * swap `setAnalyticsSink` at bootstrap to forward to Plausible/PostHog/GA.
 * No-ops on the server.
 */

export type AnalyticsEvent =
  | { name: "pageview"; path: string }
  | { name: "command_palette_open" }
  | { name: "analysis_run_triggered"; source: "analysis-page" | "command-palette" }
  | { name: "signal_notification"; count: number };

type AnalyticsSink = (event: AnalyticsEvent) => void;

const devSink: AnalyticsSink = (event) => {
  if (process.env.NODE_ENV !== "production") {
    console.debug("[analytics]", event);
  }
};

let sink: AnalyticsSink = devSink;

export function setAnalyticsSink(next: AnalyticsSink): void {
  sink = next;
}

export function track(event: AnalyticsEvent): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    sink(event);
  } catch {
    // Analytics must never break the app.
  }
}
