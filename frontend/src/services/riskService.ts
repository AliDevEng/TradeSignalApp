import { apiClient } from "@/services/api";
import type { ApiSuccessResponse } from "@/types/api";
import type { ApiPositionSize, ApiPositionSizeRequest } from "@/types/tradeApi";
import type { PositionSizeRequest } from "@/types/risk";

/**
 * Size a position via the stateless backend endpoint. The backend owns the
 * contract spec + sizing maths (and is the single source of truth), so the UI
 * never re-implements it; it only sends the trade idea + the account inputs.
 */
export async function getPositionSize(request: PositionSizeRequest): Promise<ApiPositionSize> {
  const body: ApiPositionSizeRequest = {
    pair: request.pair,
    account_balance: request.accountBalance,
    risk_percent: request.riskPercent,
    entry: request.entry,
    stop_loss: request.stopLoss,
    take_profits: request.takeProfits
  };
  const response = await apiClient.post<ApiSuccessResponse<ApiPositionSize>>(
    "/risk/position-size",
    body
  );
  return response.data.data;
}
