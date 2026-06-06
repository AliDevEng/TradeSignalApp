import { apiClient } from "@/services/api";
import type { ApiSuccessResponse } from "@/types/api";
import type { ApiCalendar } from "@/types/tradeApi";

/**
 * Fetch upcoming high-impact economic events. `withinHours` bounds the lookahead
 * window (the backend clamps it to 1..168). The endpoint always succeeds when the
 * feature is off — it returns `enabled: false` with an empty list.
 */
export async function getCalendar(withinHours = 24): Promise<ApiCalendar> {
  const response = await apiClient.get<ApiSuccessResponse<ApiCalendar>>("/calendar", {
    params: { within_hours: withinHours }
  });
  return response.data.data;
}
