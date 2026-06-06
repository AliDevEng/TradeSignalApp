"use client";

import { AlertTriangle, X } from "lucide-react";

import { useCalendar } from "@/hooks/useCalendar";
import { eventKey, nextHighImpactEvent } from "@/lib/calendar";
import { formatCountdown } from "@/lib/formatters";
import { useNow } from "@/hooks/useNow";
import { useCalendarDismissStore } from "@/store/calendarDismissStore";

/**
 * A dismissible warning banner for the next imminent high-impact event, e.g.
 * "⚠️ High-impact USD event in 2h: US CPI (YoY)". Renders nothing when there is
 * no upcoming high-impact event or the user has dismissed this one (the dismissal
 * is keyed to the event, so a later release shows the banner again).
 */
export function EconomicCalendarBanner() {
  const { events } = useCalendar();
  const now = useNow(30_000);
  const dismissed = useCalendarDismissStore((state) => state.dismissed);
  const dismiss = useCalendarDismissStore((state) => state.dismiss);

  // `useNow` is null until mounted; defer rendering so SSR and the first client
  // render agree (the banner is inherently time-relative).
  if (now === null) {
    return null;
  }

  const event = nextHighImpactEvent(events, now);
  if (!event) {
    return null;
  }

  const key = eventKey(event);
  if (dismissed.includes(key)) {
    return null;
  }

  const untilMs = new Date(event.scheduledAt).getTime() - now;

  return (
    <div
      className="flex items-start justify-between gap-3 rounded-lg border border-[#6e2029] bg-[var(--red-soft)] px-4 py-3"
      role="alert"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle aria-hidden className="mt-0.5 h-5 w-5 shrink-0 text-[var(--red-strong)]" />
        <p className="text-sm leading-6 text-[#ffd9da]">
          <span className="font-semibold text-[#fff1f1]">
            High-impact {event.currency} event in {formatCountdown(untilMs)}:
          </span>{" "}
          {event.title}
        </p>
      </div>
      <button
        aria-label="Dismiss event warning"
        className="shrink-0 rounded-md p-1 text-[#e7a3a6] transition-colors hover:bg-[#5a242b] hover:text-[#fff1f1]"
        onClick={() => dismiss(key)}
        type="button"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
