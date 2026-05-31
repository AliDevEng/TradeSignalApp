"use client";

import { RefreshCw } from "lucide-react";

import { SignalList } from "@/components/signals/SignalList";
import { SignalListSkeleton } from "@/components/signals/SignalListSkeleton";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { useSignalsQuery } from "@/hooks/useTradeQueries";
import { signals as mockSignals, tradingPairs } from "@/lib/mockSignals";

export function SignalsBrowsePage() {
  const { pairsQuery, signalsQuery } = useSignalsQuery();
  const pairs = pairsQuery.data ?? tradingPairs;
  const signals = signalsQuery.data?.signals ?? mockSignals;
  const error = pairsQuery.error ?? signalsQuery.error;
  const isLoading = (pairsQuery.isLoading || signalsQuery.isLoading) && !signalsQuery.data;

  function refresh() {
    void pairsQuery.refetch();
    void signalsQuery.refetch();
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-[#fff8df]">Signals</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Browse all generated trade setups with shareable filters and direct links into pair
            and signal detail views.
          </p>
        </div>
        <Button
          disabled={pairsQuery.isFetching || signalsQuery.isFetching}
          onClick={refresh}
          variant="primary"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {error ? (
        <ErrorState error={error} onRetry={refresh} title="Live API unavailable, showing preview data" />
      ) : null}

      {isLoading ? <SignalListSkeleton /> : <SignalList pairs={pairs} signals={signals} />}
    </section>
  );
}
