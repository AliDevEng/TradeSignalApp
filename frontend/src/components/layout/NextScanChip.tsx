"use client";

import { Loader2, Radar } from "lucide-react";

import { useNow } from "@/hooks/useNow";
import { usePipelineStatusQuery } from "@/hooks/useTradeQueries";
import { formatCountdown } from "@/lib/formatters";

/**
 * Compact, always-visible scan status for the command bar: a spinner while a scan
 * is in flight, otherwise a live countdown to the next scheduled scan. Mirrors the
 * scheduler's authoritative next-run time and ticks client-side between polls.
 * Renders nothing when the scheduler is disabled or unreachable — an enhancement,
 * never a blocker.
 */
export function NextScanChip() {
  const { data } = usePipelineStatusQuery();
  const now = useNow(1_000);

  if (!data || data.state === "disabled") {
    return null;
  }

  if (data.state === "running") {
    return (
      <span className="hidden h-9 items-center gap-2 rounded-md border border-[#6f5620] bg-[#191407] px-2.5 text-xs font-semibold text-[var(--gold-strong)] md:inline-flex">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Scanning…
      </span>
    );
  }

  if (data.next_run_at === null) {
    return null;
  }

  const targetMs = new Date(data.next_run_at).getTime();
  const countdownLabel = now === null ? "soon" : formatCountdown(targetMs - now);

  return (
    <span className="hidden h-9 items-center gap-2 rounded-md border border-[#293244] bg-[#101722] px-2.5 text-xs font-semibold text-[#9aa4b2] md:inline-flex">
      <Radar className="h-3.5 w-3.5 text-[var(--blue-strong)]" />
      <span className="hidden lg:inline">Next scan</span>
      <span className="tabular-nums text-[#dce8f7]" suppressHydrationWarning>
        {countdownLabel}
      </span>
    </span>
  );
}
