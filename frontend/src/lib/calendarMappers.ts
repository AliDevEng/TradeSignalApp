import type { ApiCalendar, ApiEconomicEvent } from "@/types/tradeApi";
import type { EconomicCalendar, EconomicEvent } from "@/types/calendar";

function mapEvent(api: ApiEconomicEvent): EconomicEvent {
  return {
    title: api.title,
    currency: api.currency,
    impact: api.impact,
    scheduledAt: api.scheduled_at
  };
}

export function mapApiCalendar(api: ApiCalendar): EconomicCalendar {
  return {
    enabled: api.enabled,
    withinHours: api.within_hours,
    // Defensive: surface events soonest-first regardless of server ordering.
    events: [...api.events]
      .map(mapEvent)
      .sort((a, b) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime())
  };
}
