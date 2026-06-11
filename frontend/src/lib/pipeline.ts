/**
 * Pure presentation helpers for the live analysis-pipeline stepper. Kept free of
 * React so the progress maths is unit-tested directly; the banner just renders
 * what these return from the {@link PipelineProgress} snapshot in the store.
 */

import { PROGRESS_PHASES, type PipelineProgress, type ProgressPhase } from "@/types/stream";

const PHASE_COUNT = PROGRESS_PHASES.length;

/** Where a given step sits relative to the run's current phase. */
export type StepStatus = "done" | "active" | "pending";

function phaseIndex(phase: ProgressPhase | null): number {
  // A live-but-not-yet-phased run (run.started before the first progress frame)
  // sits at the first step.
  return phase ? Math.max(0, PROGRESS_PHASES.indexOf(phase)) : 0;
}

/** Status of each ordered phase for the stepper, given the live snapshot. */
export function phaseStatuses(progress: PipelineProgress): { phase: ProgressPhase; status: StepStatus }[] {
  const current = phaseIndex(progress.phase);
  return PROGRESS_PHASES.map((phase, index) => ({
    phase,
    status: index < current ? "done" : index === current ? "active" : "pending"
  }));
}

/**
 * Overall completion as a 0–100 percentage for the progress bar. Each pair is one
 * unit split evenly across the phases; the in-flight pair contributes a fraction
 * from its current phase (refined by the timeframe step while fetching). Clamped,
 * so an out-of-band frame can never overflow the bar.
 */
export function pipelineProgressPercent(progress: PipelineProgress): number {
  const total = progress.pairsTotal > 0 ? progress.pairsTotal : 1;
  const index = phaseIndex(progress.phase);

  // Fraction through the current pair's phases (0–1).
  let withinPair = index / PHASE_COUNT;
  // While fetching, refine by how many timeframes have been pulled so the bar
  // moves on every candle fetch rather than jumping a whole phase at once.
  if (progress.phase === "fetching" && progress.step && progress.stepsTotal) {
    const stepFraction = Math.min(1, Math.max(0, (progress.step - 1) / progress.stepsTotal));
    withinPair = stepFraction / PHASE_COUNT;
  }

  const raw = ((progress.pairsCompleted + withinPair) / total) * 100;
  return Math.min(100, Math.max(0, Math.round(raw)));
}
