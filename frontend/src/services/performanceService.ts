import { apiClient } from "@/services/api";
import type { ApiSuccessResponse } from "@/types/api";
import type { ApiPerformance, ApiSignalType } from "@/types/tradeApi";

export type PerformanceParams = {
  pair?: string;
  signalType?: ApiSignalType;
  /** ISO 8601 lower bound on close time (maps to the `from` query param). */
  from?: string;
  /** ISO 8601 upper bound on close time (maps to the `to` query param). */
  to?: string;
};

/** Fetch the aggregated track record (summary + calibration + equity curve). */
export async function getPerformance(params: PerformanceParams = {}): Promise<ApiPerformance> {
  const response = await apiClient.get<ApiSuccessResponse<ApiPerformance>>("/performance", {
    params: {
      pair: params.pair,
      signal_type: params.signalType,
      from: params.from,
      to: params.to
    }
  });

  return response.data.data;
}
