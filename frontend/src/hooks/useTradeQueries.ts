import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { mapApiPair, mapApiSignal } from "@/lib/signalMappers";
import { getAnalysisRuns, getPairs, getSignals, triggerAnalysisRun } from "@/services/tradeService";

export const tradeQueryKeys = {
  pairs: ["pairs"] as const,
  signals: ["signals"] as const,
  analysisRuns: ["analysis-runs"] as const
};

export function usePairsQuery() {
  return useQuery({
    queryKey: tradeQueryKeys.pairs,
    queryFn: async () => {
      const pairs = await getPairs();
      return pairs.map(mapApiPair);
    },
    retry: 1,
    staleTime: 60_000
  });
}

export function useSignalsQuery() {
  const pairsQuery = usePairsQuery();

  const signalsQuery = useQuery({
    queryKey: tradeQueryKeys.signals,
    queryFn: async () => {
      const response = await getSignals({ page: 1, perPage: 50 });
      return {
        signals: response.data.map((signal) => mapApiSignal(signal, pairsQuery.data ?? [])),
        pagination: response.pagination
      };
    },
    enabled: pairsQuery.isSuccess,
    retry: 1,
    staleTime: 30_000
  });

  return {
    pairsQuery,
    signalsQuery
  };
}

export function useAnalysisRunsQuery() {
  return useQuery({
    queryKey: tradeQueryKeys.analysisRuns,
    queryFn: getAnalysisRuns,
    retry: 1,
    staleTime: 30_000
  });
}

export function useTriggerAnalysisRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: triggerAnalysisRun,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: tradeQueryKeys.analysisRuns }),
        queryClient.invalidateQueries({ queryKey: tradeQueryKeys.signals })
      ]);
    }
  });
}
