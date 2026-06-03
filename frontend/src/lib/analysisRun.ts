import type { ApiAnalysisRunStatus } from "@/types/tradeApi";

export type RunBadgeTone = "neutral" | "info" | "success" | "danger";

export const runStatusTone: Record<ApiAnalysisRunStatus, RunBadgeTone> = {
  pending: "neutral",
  running: "info",
  success: "success",
  partial: "neutral",
  failed: "danger"
};

export const runStatusOptions: ApiAnalysisRunStatus[] = [
  "pending",
  "running",
  "success",
  "partial",
  "failed"
];

/** Human run duration from start/finish timestamps, or null while in flight. */
export function formatRunDuration(startedAt: string, finishedAt: string | null): string | null {
  if (finishedAt === null) {
    return null;
  }

  const ms = new Date(finishedAt).getTime() - new Date(startedAt).getTime();
  if (!Number.isFinite(ms) || ms < 0) {
    return null;
  }

  if (ms < 1_000) {
    return `${ms} ms`;
  }

  const seconds = ms / 1_000;
  if (seconds < 60) {
    return `${seconds.toFixed(1)} s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return `${minutes}m ${remainder}s`;
}
