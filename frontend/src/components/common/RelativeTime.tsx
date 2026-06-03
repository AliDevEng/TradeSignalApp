"use client";

import { useNow } from "@/hooks/useNow";
import { formatDateTime, formatRelativeTime } from "@/lib/formatters";

type RelativeTimeProps = {
  /** ISO timestamp, epoch ms, or Date to describe relative to now. */
  value: string | number | Date;
  /** How often to re-tick. Defaults to once per second. */
  intervalMs?: number;
  /** Optional prefix, e.g. "updated". */
  prefix?: string;
  className?: string;
};

/**
 * A live "x ago" / "in x" label that ticks on an interval. Before mount it
 * renders an absolute timestamp so the markup is stable across hydration.
 */
export function RelativeTime({ value, intervalMs = 1_000, prefix, className }: RelativeTimeProps) {
  const now = useNow(intervalMs);
  const label = now === null ? formatDateTime(value as string) : formatRelativeTime(value, now);
  const title = typeof value === "object" ? value.toISOString() : String(value);

  return (
    <time className={className} dateTime={title} suppressHydrationWarning title={title}>
      {prefix ? `${prefix} ` : ""}
      {label}
    </time>
  );
}
