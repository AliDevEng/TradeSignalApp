"use client";

import { Clock3, Loader2 } from "lucide-react";

import { useNow } from "@/hooks/useNow";
import { usePipelineStatusQuery } from "@/hooks/useTradeQueries";
import { formatCountdown } from "@/lib/formatters";
import { cn } from "@/lib/utils";

type PipelineStatusBannerProps = {
  className?: string;
};

/**
 * Surfaces the otherwise-invisible background analysis pipeline: a "processing"
 * state while a scan is in flight, and a live countdown to the next scheduled
 * scan when idle. Self-contained (owns its own query) so it can be dropped onto
 * any page without prop drilling.
 *
 * Renders nothing when the scheduler is disabled, the status hasn't loaded, or
 * the API is unreachable — it's an enhancement, never a blocker. Server and
 * first client render agree because the query has no prefetched data (both emit
 * `null`), so there's no hydration mismatch.
 */
export function PipelineStatusBanner({ className }: PipelineStatusBannerProps) {
  const { data } = usePipelineStatusQuery();
  const now = useNow(1_000);

  if (!data || data.state === "disabled") {
    return null;
  }

  if (data.state === "running") {
    return (
      <div
        aria-live="polite"
        className={cn(
          "flex items-center gap-3 rounded-lg border border-[#6f5620] bg-[#191407] px-4 py-3",
          className
        )}
      >
        <Loader2 className="h-5 w-5 shrink-0 animate-spin text-[var(--gold-strong)]" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[#fff8df]">Analyzing the market…</p>
          <p className="text-xs leading-5 text-[#c7b98d]">
            Fetching prices, scoring setups, and asking the model. Fresh signals
            appear here automatically the moment the scan finishes.
          </p>
        </div>
      </div>
    );
  }

  // Idle: count down to the scheduler's next fire time. Without one (e.g. the
  // job hasn't been scheduled yet) there's nothing meaningful to show.
  if (data.next_run_at === null) {
    return null;
  }

  // `now` is null until the clock mounts (one render); show a neutral label
  // for that frame rather than reaching for an impure `Date.now()` in render.
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
