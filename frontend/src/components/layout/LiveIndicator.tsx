"use client";

import { cn } from "@/lib/utils";
import type { StreamStatus } from "@/types/stream";

const PRESENTATION: Record<StreamStatus, { label: string; dot: string; text: string }> = {
  live: {
    label: "Live — receiving real-time updates",
    dot: "bg-[var(--green,#3fb950)] animate-pulse",
    text: "text-[#9aa4b2]"
  },
  connecting: {
    label: "Connecting to the live stream",
    dot: "bg-[var(--gold,#d8af4f)] animate-pulse",
    text: "text-[#9aa4b2]"
  },
  offline: {
    label: "Live stream offline — falling back to polling",
    dot: "bg-[#566174]",
    text: "text-[#6f7b8e]"
  }
};

const LABELS: Record<StreamStatus, string> = {
  live: "Live",
  connecting: "Connecting",
  offline: "Offline"
};

/**
 * A small connection indicator for the SSE stream. Shows a coloured dot + label
 * so the user knows whether the dashboard is updating in real time or has
 * fallen back to polling. Accessible: the dot is decorative and the live status
 * is exposed via an `aria-label`/`title`.
 */
export function LiveIndicator({ status }: { status: StreamStatus }) {
  const presentation = PRESENTATION[status];

  return (
    <span
      aria-label={presentation.label}
      className={cn(
        "hidden items-center gap-1.5 rounded-md border border-[#293244] bg-[#101722] px-2 py-1.5 text-xs font-semibold sm:inline-flex",
        presentation.text
      )}
      role="status"
      title={presentation.label}
    >
      <span aria-hidden className={cn("h-2 w-2 rounded-full", presentation.dot)} />
      {LABELS[status]}
    </span>
  );
}
