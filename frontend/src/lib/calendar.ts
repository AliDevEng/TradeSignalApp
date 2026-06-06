/**
 * Pure helpers for the economic-calendar surfaces — event selection, grouping,
 * keys, and impact presentation. Kept free of React so the selection logic is
 * unit-tested directly; the banner/strip components render the results.
 */

import type { EconomicEvent } from "@/types/calendar";

/** A stable identity for an event, used to remember dismissals. */
export function eventKey(event: EconomicEvent): string {
  return `${event.scheduledAt}::${event.currency}::${event.title}`;
}

export function isHighImpact(event: EconomicEvent): boolean {
  return event.impact.toLowerCase() === "high";
}

/**
 * The soonest still-upcoming high-impact event, or `null`. This is what the
 * dismissible banner warns about — the next release that could move the trade.
 */
export function nextHighImpactEvent(
  events: EconomicEvent[],
  now: number = Date.now()
): EconomicEvent | null {
  const upcoming = events
    .filter((event) => isHighImpact(event) && new Date(event.scheduledAt).getTime() > now)
    .sort((a, b) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime());
  return upcoming[0] ?? null;
}

export type EventDayGroup = {
  /** A `YYYY-MM-DD` key for the day (UTC-stable grouping). */
  dayKey: string;
  /** A human day label, e.g. "Today", "Tomorrow", or "Jun 9". */
  label: string;
  events: EconomicEvent[];
};

function dayKeyOf(iso: string): string {
  return new Date(iso).toISOString().slice(0, 10);
}

/**
 * Group upcoming events by calendar day for the dashboard strip, soonest day
 * first, dropping anything already in the past relative to `now`.
 */
export function groupEventsByDay(
  events: EconomicEvent[],
  now: number = Date.now()
): EventDayGroup[] {
  const todayKey = new Date(now).toISOString().slice(0, 10);
  const tomorrowKey = new Date(now + 86_400_000).toISOString().slice(0, 10);

  const groups = new Map<string, EconomicEvent[]>();
  for (const event of events) {
    if (new Date(event.scheduledAt).getTime() <= now) {
      continue;
    }
    const key = dayKeyOf(event.scheduledAt);
    const bucket = groups.get(key);
    if (bucket) {
      bucket.push(event);
    } else {
      groups.set(key, [event]);
    }
  }

  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([dayKey, dayEvents]) => ({
      dayKey,
      label: dayKey === todayKey ? "Today" : dayKey === tomorrowKey ? "Tomorrow" : labelFor(dayKey),
      events: dayEvents.sort(
        (a, b) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime()
      )
    }));
}

function labelFor(dayKey: string): string {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(
    new Date(`${dayKey}T00:00:00Z`)
  );
}

export type ImpactTone = "danger" | "gold" | "muted";

export function impactTone(event: EconomicEvent): ImpactTone {
  const impact = event.impact.toLowerCase();
  if (impact === "high") {
    return "danger";
  }
  if (impact === "medium") {
    return "gold";
  }
  return "muted";
}

/**
 * Sample events for preview mode (no live calendar / feature disabled). Anchored
 * relative to `now` so they are always "upcoming" in a demo. Only used when
 * `PREVIEW_DATA_ENABLED` — never presented as live data in production.
 */
export function mockCalendarEvents(now: number = Date.now()): EconomicEvent[] {
  return [
    {
      title: "US CPI (YoY)",
      currency: "USD",
      impact: "high",
      scheduledAt: new Date(now + 2 * 3_600_000).toISOString()
    },
    {
      title: "FOMC Press Conference",
      currency: "USD",
      impact: "high",
      scheduledAt: new Date(now + 26 * 3_600_000).toISOString()
    },
    {
      title: "Unemployment Claims",
      currency: "USD",
      impact: "medium",
      scheduledAt: new Date(now + 28 * 3_600_000).toISOString()
    }
  ];
}
