"use client";

import { useMemo, useSyncExternalStore } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { RefreshCw, X } from "lucide-react";

import { RelativeTime } from "@/components/common/RelativeTime";
import { SignalCard } from "@/components/signals/SignalCard";
import { SignalFilters } from "@/components/signals/SignalFilters";
import { SignalListSkeleton } from "@/components/signals/SignalListSkeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { useInfiniteSignalsQuery } from "@/hooks/useTradeQueries";
import { refineSignals } from "@/lib/signalFilters";
import { signals as mockSignals, tradingPairs } from "@/lib/mockSignals";
import { useSignalStore } from "@/store/signalStore";
import { useUIStore } from "@/store/uiStore";
import type { Signal } from "@/types/signal";

const emptySignals: Signal[] = [];
const subscribeToHydration = () => () => undefined;

export function SignalsBrowsePage() {
  const searchParams = useSearchParams();
  const pairParam = searchParams.get("pair");
  const runParam = searchParams.get("run");
  const pairFilter = pairParam && pairParam !== "all" ? pairParam : undefined;

  const query = useInfiniteSignalsQuery({ pair: pairFilter, runId: runParam ?? undefined });

  const direction = useSignalStore((state) => state.direction);
  const tradeStyle = useSignalStore((state) => state.tradeStyle);
  const status = useSignalStore((state) => state.status);
  const storePair = useSignalStore((state) => state.pair);
  const sort = useSignalStore((state) => state.sort);
  const reset = useSignalStore((state) => state.reset);
  const density = useUIStore((state) => state.density);
  const hasMounted = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false
  );

  const isQueryError = hasMounted && query.isError;
  const hasLiveData = hasMounted && query.isSuccess && query.signals.length >= 0 && !query.isError;
  const pairs = hasMounted && query.pairs.length > 0 ? query.pairs : tradingPairs;
  const sourceSignals = isQueryError ? mockSignals : hasMounted ? query.signals : emptySignals;

  // The pair filter is enforced server-side, so it's a no-op refinement here;
  // direction/style/status/sort are applied client-side over the loaded pages.
  const visibleSignals = useMemo(
    () => refineSignals(sourceSignals, { direction, tradeStyle, status, pair: storePair, sort }),
    [sourceSignals, direction, tradeStyle, status, storePair, sort]
  );

  const isInitialLoading = !hasMounted || (query.isLoading && !query.isError);

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-[#fff8df]">Signals</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Browse all generated trade setups with shareable filters and server-side pagination
            straight into pair and signal detail views.
          </p>
          {hasLiveData ? (
            <p className="mt-2 text-xs font-medium text-[var(--muted)]">
              {query.total} total signals ·{" "}
              <RelativeTime prefix="updated" value={query.dataUpdatedAt} intervalMs={5_000} />
            </p>
          ) : null}
        </div>
        <Button disabled={!hasMounted || query.isFetching} onClick={() => void query.refetch()} variant="primary">
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {runParam ? (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[#234f86] bg-[var(--blue-soft)] px-4 py-3">
          <Badge tone="info">Filtered by run</Badge>
          <code className="truncate text-xs text-[#b9c7d9]">{runParam}</code>
          <Link
            className="ml-auto inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--blue-strong)] hover:text-[#8ab8ff]"
            href="/signals"
          >
            <X className="h-3.5 w-3.5" />
            Clear run filter
          </Link>
        </div>
      ) : null}

      {isQueryError ? (
        <ErrorState
          error={query.error as Error}
          onRetry={() => void query.refetch()}
          title="Live API unavailable, showing preview data"
        />
      ) : null}

      <SignalFilters pairs={pairs} />

      {isInitialLoading ? (
        <SignalListSkeleton />
      ) : visibleSignals.length > 0 ? (
        <div className="grid gap-4">
          {visibleSignals.map((signal) => (
            <SignalCard density={density} key={signal.id} signal={signal} />
          ))}
        </div>
      ) : (
        <EmptyState
          action={
            <Button onClick={reset} variant="primary">
              Reset filters
            </Button>
          }
          description="No signals match these filters yet. Adjust direction, status, or pair to widen the search."
          title="No signals to show"
        />
      )}

      {query.hasNextPage && !query.isError ? (
        <div className="flex justify-center">
          <Button
            disabled={query.isFetchingNextPage}
            onClick={() => void query.fetchNextPage()}
            variant="secondary"
          >
            {query.isFetchingNextPage ? "Loading…" : "Load more signals"}
          </Button>
        </div>
      ) : null}
    </section>
  );
}
