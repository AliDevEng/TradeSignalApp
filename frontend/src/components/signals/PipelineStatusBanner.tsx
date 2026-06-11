"use client";

import { Check, Clock3, Loader2 } from "lucide-react";

import { useNow } from "@/hooks/useNow";
import { usePipelineStatusQuery } from "@/hooks/useTradeQueries";
import { formatCountdown } from "@/lib/formatters";
import { phaseStatuses, pipelineProgressPercent, type StepStatus } from "@/lib/pipeline";
import { cn } from "@/lib/utils";
import { usePipelineProgressStore } from "@/store/pipelineProgressStore";
import { PROGRESS_PHASE_LABELS, type PipelineProgress } from "@/types/stream";

type PipelineStatusBannerProps = {
  className?: string;
};

/**
 * Surfaces the otherwise-invisible background analysis pipeline. While a scan is
 * in flight it shows a live workflow stepper — Loading market data → AI analyzing
 * → Scoring setups → Saving signals — driven by real-time `run.progress` events,
 * so the user sees exactly which stage the AI is at. When idle it shows a live
 * countdown to the next scheduled scan. Self-contained (owns its own query +
 * store read) so it can be dropped onto any page without prop drilling.
 *
 * Renders nothing when the scheduler is disabled, the status hasn't loaded, or
 * the API is unreachable — it's an enhancement, never a blocker.
 */
export function PipelineStatusBanner({ className }: PipelineStatusBannerProps) {
  const { data } = usePipelineStatusQuery();
  const progress = usePipelineProgressStore((state) => state.progress);
  const now = useNow(1_000);

  if (!data || data.state === "disabled") {
    return null;
  }

  // A live progress snapshot means a run is in flight even if the 15s poll hasn't
  // caught up yet — so treat either signal as "running".
  const isRunning = data.state === "running" || progress !== null;

  if (isRunning) {
    return <RunningBanner progress={progress} className={className} />;
  }

  // Idle: count down to the scheduler's next fire time. Without one there's
  // nothing meaningful to show.
  if (data.next_run_at === null) {
    return null;
  }

  // `now` is null until the clock mounts (one render); show a neutral label for
  // that frame rather than reaching for an impure `Date.now()` in render.
  const targetMs = new Date(data.next_run_at).getTime();
  const countdownLabel = now === null ? "soon" : formatCountdown(targetMs - now);

  return (
    <div
      aria-live="polite"
      className={cn(
        "flex items-center gap-3 rounded-lg border border-[#244d7d] bg-[var(--blue-soft)] px-4 py-3",
        className
      )}
    >
      <Clock3 className="h-5 w-5 shrink-0 text-[var(--blue-strong)]" />
      <div className="min-w-0">
        <p className="text-sm font-semibold text-[#dce8f7]">
          Next market scan in{" "}
          <span className="font-bold text-[var(--blue-strong)]" suppressHydrationWarning>
            {countdownLabel}
          </span>
        </p>
        <p className="text-xs leading-5 text-[#b9c7d9]">
          Signals refresh automatically after each scan — no need to reload.
        </p>
      </div>
    </div>
  );
}

function RunningBanner({
  progress,
  className
}: {
  progress: PipelineProgress | null;
  className?: string;
}) {
  // Without a detailed progress frame (e.g. the SSE stream is off and only the
  // poll reports "running") fall back to an indeterminate "fetching" view.
  const snapshot: PipelineProgress = progress ?? {
    runId: "",
    phase: null,
    message: "Fetching prices, scoring setups, and asking the model.",
    pair: null,
    pairsTotal: 0,
    pairsCompleted: 0,
    step: null,
    stepsTotal: null,
    // Unused in the fallback (no progress bar without a real frame); a constant
    // keeps render pure rather than reaching for an impure `Date.now()`.
    updatedAt: 0
  };
  const steps = phaseStatuses(snapshot);
  const percent = progress ? pipelineProgressPercent(snapshot) : null;

  const detail =
    snapshot.pair && snapshot.message
      ? `${snapshot.message} · ${snapshot.pair}`
      : snapshot.message || "Analyzing the market…";

  return (
    <div
      aria-live="polite"
      className={cn(
        "rounded-lg border border-[#6f5620] bg-[#191407] px-4 py-3",
        className
      )}
    >
      <div className="flex items-center gap-3">
        <Loader2 className="h-5 w-5 shrink-0 animate-spin text-[var(--gold-strong)]" />
        <p className="text-sm font-semibold text-[#fff8df]">Analyzing the market…</p>
        {percent !== null ? (
          <span className="ml-auto text-xs font-bold tabular-nums text-[var(--gold-strong)]">
            {percent}%
          </span>
        ) : null}
      </div>

      {/* The workflow stepper: one pill per phase, the active one highlighted. */}
      <ol className="mt-3 flex flex-wrap items-center gap-1.5">
        {steps.map(({ phase, status }) => (
          <li key={phase}>
            <StepPill label={PROGRESS_PHASE_LABELS[phase]} status={status} />
          </li>
        ))}
      </ol>

      {/* Determinate progress bar (only with real per-phase data). */}
      {percent !== null ? (
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[#2a2110]">
          <div
            className="h-full rounded-full bg-[var(--gold-strong)] transition-[width] duration-500 ease-out"
            style={{ width: `${percent}%` }}
          />
        </div>
      ) : null}

      <p className="mt-2 text-xs leading-5 text-[#c7b98d]">
        {detail}
        {snapshot.pairsTotal > 1 ? (
          <span className="text-[#9a8c63]">
            {" "}
            · pair {Math.min(snapshot.pairsCompleted + 1, snapshot.pairsTotal)}/{snapshot.pairsTotal}
          </span>
        ) : null}
        {" "}Fresh signals appear automatically the moment the scan finishes.
      </p>
    </div>
  );
}

function StepPill({ label, status }: { label: string; status: StepStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-semibold",
        status === "done" && "border-[#3c5a2e] bg-[#16210f] text-[#9fd08a]",
        status === "active" &&
          "border-[#7a5f1f] bg-[#241b08] text-[var(--gold-strong)] shadow-[0_0_0_1px_rgba(212,175,55,0.25)]",
        status === "pending" && "border-[#332a16] bg-transparent text-[#7a6f50]"
      )}
    >
      {status === "done" ? (
        <Check className="h-3 w-3" aria-hidden />
      ) : status === "active" ? (
        <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
      ) : (
        <span className="h-1.5 w-1.5 rounded-full bg-current opacity-60" aria-hidden />
      )}
      {label}
    </span>
  );
}
