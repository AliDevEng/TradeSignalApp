"use client";

import { CalendarClock } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { useCalendar } from "@/hooks/useCalendar";
import { groupEventsByDay, impactTone, type ImpactTone } from "@/lib/calendar";
import { useNow } from "@/hooks/useNow";
import type { EconomicEvent } from "@/types/calendar";

const TONE_CLASS: Record<ImpactTone, string> = {
  danger: "border-[#6e2029] bg-[var(--red-soft)] text-[#ffd9da]",
  gold: "border-[#6f5620] bg-[#1a1407] text-[var(--gold-strong)]",
  muted: "border-[#263247] bg-[#101722] text-[var(--muted)]"
};

function eventTime(iso: string): string {
  return new Intl.DateTimeFormat("en", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

/**
 * A compact per-day strip of upcoming high-impact macro events on the dashboard,
 * grouped by day (Today / Tomorrow / date). Renders nothing when there are no
 * upcoming events, so it stays out of the way when the calendar is quiet or off.
 */
export function EconomicEventStrip() {
  const { events } = useCalendar(72);
  const now = useNow(60_000);

  if (now === null) {
    return null;
  }

  const days = groupEventsByDay(events, now);
  if (days.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader className="flex items-center gap-2 py-3">
        <CalendarClock className="h-4 w-4 text-[var(--gold)]" />
        <h2 className="text-sm font-semibold text-[#fff8df]">Economic calendar</h2>
      </CardHeader>
      <CardContent className="space-y-3 py-3">
        {days.map((day) => (
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start" key={day.dayKey}>
            <p className="w-20 shrink-0 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
              {day.label}
            </p>
            <ul className="flex flex-wrap gap-2">
              {day.events.map((event) => (
                <EventChip event={event} key={`${event.scheduledAt}-${event.title}`} />
              ))}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function EventChip({ event }: { event: EconomicEvent }) {
  return (
    <li
      className={`inline-flex items-center gap-2 rounded-md border px-2.5 py-1 text-xs ${TONE_CLASS[impactTone(event)]}`}
    >
      <span className="font-semibold tabular-nums">{eventTime(event.scheduledAt)}</span>
      <span className="font-semibold">{event.currency}</span>
      <span className="text-[#cdd6e3]">{event.title}</span>
    </li>
  );
}
