import { apiClient } from "@/services/api";
import type { ApiSuccessResponse, PaginatedResponse } from "@/types/api";
import type { ApiAnalysisRun, ApiPair, ApiSignal } from "@/types/tradeApi";

type SignalListParams = {
  page?: number;
  perPage?: number;
  pair?: string;
  runId?: string;
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
      run_id: params.runId
    }
  });

  return response.data;
}

export async function getSignal(signalId: string): Promise<ApiSignal> {
  const response = await apiClient.get<ApiSuccessResponse<ApiSignal>>(`/signals/${signalId}`);
  return response.data.data;
}

export async function getPairSignals(symbol: string): Promise<ApiSignal[]> {
  const response = await apiClient.get<ApiSuccessResponse<ApiSignal[]>>(`/pairs/${symbol}/signals`, {
    params: {
      limit: 20
    }
  });

  return response.data.data;
}

export async function getAnalysisRuns(): Promise<PaginatedResponse<ApiAnalysisRun>> {
  const response = await apiClient.get<PaginatedResponse<ApiAnalysisRun>>("/analysis/runs", {
    params: {
      page: 1,
      per_page: 10
    }
  });

  return response.data;
}

export async function triggerAnalysisRun(): Promise<void> {
  await apiClient.post<ApiSuccessResponse<{ status: "accepted"; detail: string }>>("/analysis/runs");
}
