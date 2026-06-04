import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient
} from "@tanstack/react-query";

import { mapApiPerformance } from "@/lib/performanceMappers";
import { mapApiPair, mapApiSignal } from "@/lib/signalMappers";
import { getPerformance, type PerformanceParams } from "@/services/performanceService";
import {
  getAnalysisRun,
  getAnalysisRuns,
  getPairs,
  getRunSignals,
  getSignal,
  getSignals,
  triggerAnalysisRun,
  type AnalysisRunListParams,
  type SignalListParams
} from "@/services/tradeService";
import type { TradingPair } from "@/types/signal";

/** Auto-refresh cadences. The backend scheduler runs every 15 min, so these are
 * tuned to surface fresh data quickly without hammering the API. */
export const REFETCH_INTERVALS = {
  signals: 30_000,
  analysisRuns: 20_000,
  performance: 60_000
} as const;

const DASHBOARD_PAGE_SIZE = 20;
const BROWSE_PAGE_SIZE = 12;

export const tradeQueryKeys = {
  pairs: ["pairs"] as const,
  signals: (params: SignalListParams) => ["signals", params] as const,
  signalsInfinite: (params: SignalListParams) => ["signals", "infinite", params] as const,
  signal: (signalId: string) => ["signal", signalId] as const,
  analysisRuns: (params: AnalysisRunListParams) => ["analysis-runs", params] as const,
  analysisRun: (runId: string) => ["analysis-run", runId] as const,
  runSignals: (runId: string) => ["analysis-run", runId, "signals"] as const,
  performance: (params: PerformanceParams) => ["performance", params] as const
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

type UseSignalsOptions = SignalListParams & {
  /** Pass `false` to disable polling (e.g. background tabs). */
  autoRefresh?: boolean;
};

/**
 * The dashboard's signal feed: first page, mapped to domain signals, with
 * pairs resolved for symbol/display-name lookups. Pairs and signals are
 * separate queries so a pairs failure doesn't blank the signal feed.
 */
export function useSignalsQuery(options: UseSignalsOptions = {}) {
  const { autoRefresh = true, ...params } = options;
  const pairsQuery = usePairsQuery();
  const listParams: SignalListParams = {
    page: params.page ?? 1,
    perPage: params.perPage ?? DASHBOARD_PAGE_SIZE,
    pair: params.pair,
    runId: params.runId
  };

  const signalsQuery = useQuery({
    queryKey: tradeQueryKeys.signals(listParams),
    queryFn: async () => {
      const response = await getSignals(listParams);
      return {
        signals: response.data.map((signal) => mapApiSignal(signal, pairsQuery.data ?? [])),
        pagination: response.pagination
      };
    },
    enabled: pairsQuery.isSuccess,
    retry: 1,
    staleTime: 15_000,
    refetchInterval: autoRefresh ? REFETCH_INTERVALS.signals : false
  });

  return { pairsQuery, signalsQuery };
}

/**
 * Server-side paginated signal browse, driven by `pair`/`run_id` filters with a
 * "load more" affordance. Pages accumulate so the list grows as the user pulls
 * more from the backend.
 */
export function useInfiniteSignalsQuery(params: Pick<SignalListParams, "pair" | "runId"> = {}) {
  const pairsQuery = usePairsQuery();
  const pairs = pairsQuery.data ?? [];

  const query = useInfiniteQuery({
    queryKey: tradeQueryKeys.signalsInfinite(params),
    enabled: pairsQuery.isSuccess,
    initialPageParam: 1,
    queryFn: async ({ pageParam }) => {
      const response = await getSignals({
        page: pageParam,
        perPage: BROWSE_PAGE_SIZE,
        pair: params.pair,
        runId: params.runId
      });
      return response;
    },
    getNextPageParam: (lastPage) => {
      const { page, pages } = lastPage.pagination;
      return page < pages ? page + 1 : undefined;
    },
    retry: 1,
    staleTime: 15_000
  });

  const signals = (query.data?.pages ?? []).flatMap((page) =>
    page.data.map((signal) => mapApiSignal(signal, pairs))
  );
  const total = query.data?.pages.at(-1)?.pagination.total ?? signals.length;

  return { ...query, pairsQuery, pairs: pairs as TradingPair[], signals, total };
}

export function useSignalQuery(signalId: string) {
  const pairsQuery = usePairsQuery();

  const signalQuery = useQuery({
    queryKey: tradeQueryKeys.signal(signalId),
    queryFn: async () => {
      const signal = await getSignal(signalId);
      return mapApiSignal(signal, pairsQuery.data ?? []);
    },
    enabled: pairsQuery.isSuccess,
    retry: 1,
    staleTime: 15_000,
    refetchInterval: REFETCH_INTERVALS.signals
  });

  return { pairsQuery, signalQuery };
}

export function useAnalysisRunsQuery(params: AnalysisRunListParams = {}) {
  const listParams: AnalysisRunListParams = {
    page: params.page ?? 1,
    perPage: params.perPage ?? 10,
    status: params.status
  };

  return useQuery({
    queryKey: tradeQueryKeys.analysisRuns(listParams),
    queryFn: () => getAnalysisRuns(listParams),
    retry: 1,
    staleTime: 15_000,
    refetchInterval: REFETCH_INTERVALS.analysisRuns
  });
}

export function useAnalysisRunQuery(runId: string) {
  return useQuery({
    queryKey: tradeQueryKeys.analysisRun(runId),
    queryFn: () => getAnalysisRun(runId),
    retry: 1,
    staleTime: 15_000,
    refetchInterval: REFETCH_INTERVALS.analysisRuns
  });
}

export function useRunSignalsQuery(runId: string) {
  const pairsQuery = usePairsQuery();

  const signalsQuery = useQuery({
    queryKey: tradeQueryKeys.runSignals(runId),
    queryFn: async () => {
      const signals = await getRunSignals(runId);
      return signals.map((signal) => mapApiSignal(signal, pairsQuery.data ?? []));
    },
    enabled: pairsQuery.isSuccess,
    retry: 1,
    staleTime: 15_000
  });

  return { pairsQuery, signalsQuery };
}

/**
 * The aggregated track record (summary + calibration + equity curve), mapped to
 * the domain {@link Performance} shape. Auto-refreshes on the performance cadence
 * — closures trickle in slowly, so a slower poll than the live signal feed.
 */
export function usePerformanceQuery(params: PerformanceParams = {}) {
  return useQuery({
    queryKey: tradeQueryKeys.performance(params),
    queryFn: async () => mapApiPerformance(await getPerformance(params)),
    retry: 1,
    staleTime: 30_000,
    refetchInterval: REFETCH_INTERVALS.performance
  });
}

export function useTriggerAnalysisRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: triggerAnalysisRun,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["analysis-runs"] });
      await queryClient.invalidateQueries({ queryKey: ["signals"] });
    }
  });
}
