import { apiClient } from "@/services/api";
import type { ApiSuccessResponse, PaginatedResponse } from "@/types/api";
import type {
  ApiAnalysisRun,
  ApiAnalysisRunStatus,
  ApiPair,
  ApiPipelineStatus,
  ApiSignal,
  ApiSignalType
} from "@/types/tradeApi";

export type SignalDirectionFilter = "buy" | "sell" | "neutral";
export type SignalStatusFilter = "active" | "watchlist" | "expired";
export type SignalResultFilter = "open" | "win" | "loss" | "expired";
export type SignalSort = "confidence" | "newest" | "symbol";

export type SignalListParams = {
  page?: number;
  perPage?: number;
  pair?: string;
  runId?: string;
  signalType?: ApiSignalType;
  direction?: SignalDirectionFilter;
  status?: SignalStatusFilter;
  /** Result category: a "win" is any take-profit rung. */
  result?: SignalResultFilter;
  sort?: SignalSort;
};

export type AnalysisRunListParams = {
  page?: number;
  perPage?: number;
  status?: ApiAnalysisRunStatus;
};

export async function getPairs(): Promise<ApiPair[]> {
  const response = await apiClient.get<ApiSuccessResponse<ApiPair[]>>("/pairs");
  return response.data.data;
}

export async function getPair(symbol: string): Promise<ApiPair> {
  const response = await apiClient.get<ApiSuccessResponse<ApiPair>>(`/pairs/${symbol}`);
  return response.data.data;
}

export async function getSignals(params: SignalListParams = {}): Promise<PaginatedResponse<ApiSignal>> {
  const response = await apiClient.get<PaginatedResponse<ApiSignal>>("/signals", {
    params: {
      page: params.page,
      per_page: params.perPage,
      pair: params.pair,
      run_id: params.runId,
      signal_type: params.signalType,
      direction: params.direction,
      status: params.status,
      result: params.result,
      sort: params.sort
    }
  });

  return response.data;
}

export async function getSignal(signalId: string): Promise<ApiSignal> {
  const response = await apiClient.get<ApiSuccessResponse<ApiSignal>>(`/signals/${signalId}`);
  return response.data.data;
}

export async function getPairSignals(
  symbol: string,
  limit = 20,
  signalType?: ApiSignalType
): Promise<ApiSignal[]> {
  const response = await apiClient.get<ApiSuccessResponse<ApiSignal[]>>(`/pairs/${symbol}/signals`, {
    params: { limit, signal_type: signalType }
  });

  return response.data.data;
}

export async function getAnalysisRuns(
  params: AnalysisRunListParams = {}
): Promise<PaginatedResponse<ApiAnalysisRun>> {
  const response = await apiClient.get<PaginatedResponse<ApiAnalysisRun>>("/analysis/runs", {
    params: {
      page: params.page ?? 1,
      per_page: params.perPage ?? 10,
      status: params.status
    }
  });

  return response.data;
}

export async function getPipelineStatus(): Promise<ApiPipelineStatus> {
  const response = await apiClient.get<ApiSuccessResponse<ApiPipelineStatus>>("/analysis/status");
  return response.data.data;
}

export async function getAnalysisRun(runId: string): Promise<ApiAnalysisRun> {
  const response = await apiClient.get<ApiSuccessResponse<ApiAnalysisRun>>(`/analysis/runs/${runId}`);
  return response.data.data;
}

export async function getRunSignals(runId: string): Promise<ApiSignal[]> {
  const response = await apiClient.get<ApiSuccessResponse<ApiSignal[]>>(`/analysis/runs/${runId}/signals`);
  return response.data.data;
}

export async function triggerAnalysisRun(): Promise<void> {
  await apiClient.post<ApiSuccessResponse<{ status: "accepted"; detail: string }>>("/analysis/runs");
}
