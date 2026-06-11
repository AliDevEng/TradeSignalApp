"use client";

import { create } from "zustand";

import type { PipelineProgress } from "@/types/stream";

/**
 * Live progress of the in-flight analysis run, fed from the SSE stream
 * (`run.started` / `run.progress` / `run.finished`). It's the real-time view of
 * the otherwise-invisible background pipeline — the workflow stepper reads it.
 *
 * Kept separate from the polled `/analysis/status` query (which owns the coarse
 * running/idle state + the next-run countdown): this store carries the *detailed*
 * phase narration that only the stream provides. The banner blends the two —
 * polled status decides running-vs-idle, this store enriches "running" with the
 * exact phase. Cleared on `run.finished`, so a finished run shows nothing stale.
 */
type PipelineProgressState = {
  progress: PipelineProgress | null;
  /** Replace the current snapshot (newer `run.started`/`run.progress` frame). */
  setProgress: (progress: PipelineProgress) => void;
  /** Clear progress for a given run when it finishes (id-guarded against races). */
  clearForRun: (runId: string) => void;
  /** Clear unconditionally. */
  clear: () => void;
};

export const usePipelineProgressStore = create<PipelineProgressState>((set) => ({
  progress: null,
  setProgress: (progress) =>
    set((state) => {
      // Ignore a frame for an older run if a newer one has already started —
      // out-of-order delivery must never resurrect a stale run's phase.
      if (
        state.progress &&
        state.progress.runId !== progress.runId &&
        progress.updatedAt < state.progress.updatedAt
      ) {
        return state;
      }
      return { progress };
    }),
  clearForRun: (runId) =>
    set((state) =>
      state.progress && state.progress.runId !== runId ? state : { progress: null }
    ),
  clear: () => set({ progress: null })
}));
