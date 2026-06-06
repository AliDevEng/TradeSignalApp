import { useQuery } from "@tanstack/react-query";

import { PREVIEW_DATA_ENABLED } from "@/lib/env";
import { mockCalendarEvents } from "@/lib/calendar";
import { mapApiCalendar } from "@/lib/calendarMappers";
import { getCalendar } from "@/services/calendarService";
import type { EconomicEvent } from "@/types/calendar";

/**
 * Upcoming high-impact economic events for the dashboard banner + strip.
 *
 * Returns the live events when the backend calendar is enabled and has any. In
 * preview mode only (`NEXT_PUBLIC_PREVIEW_DATA`), it falls back to bundled sample
 * events when the feature is off or the API is unreachable — never presenting
 * fabricated macro data as live in production, the same discipline as the other
 * preview fallbacks.
 */
export function useCalendar(withinHours = 24): { events: EconomicEvent[]; isLoading: boolean } {
  const query = useQuery({
    queryKey: ["calendar", withinHours],
    queryFn: async () => mapApiCalendar(await getCalendar(withinHours)),
    retry: 1,
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000
  });

  if (query.data && query.data.events.length > 0) {
    return { events: query.data.events, isLoading: false };
  }

  // Feature disabled / nothing scheduled / API error: show samples only in preview.
  if (PREVIEW_DATA_ENABLED && (query.isError || query.data?.enabled === false || query.data)) {
    return { events: mockCalendarEvents(), isLoading: false };
  }

  return { events: [], isLoading: query.isLoading };
}
