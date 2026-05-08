"use client";

import { SignalCard } from "@/components/signals/SignalCard";
import { SignalFilters } from "@/components/signals/SignalFilters";
import { Button } from "@/components/ui/Button";
import { useSignalStore } from "@/store/signalStore";
import { useUIStore } from "@/store/uiStore";
import type { Signal, TradingPair } from "@/types/signal";

type SignalListProps = {
  signals: Signal[];
  pairs: TradingPair[];
};

function sortSignals(signals: Signal[], sort: ReturnType<typeof useSignalStore.getState>["sort"]) {
  return [...signals].sort((first, second) => {
    if (sort === "newest") {
      return new Date(second.generatedAt).getTime() - new Date(first.generatedAt).getTime();
    }

    if (sort === "symbol") {
      return first.symbol.localeCompare(second.symbol);
    }

    return second.confidence - first.confidence;
  });
}

export function SignalList({ signals, pairs }: SignalListProps) {
  const direction = useSignalStore((state) => state.direction);
  const status = useSignalStore((state) => state.status);
  const pair = useSignalStore((state) => state.pair);
  const sort = useSignalStore((state) => state.sort);
  const reset = useSignalStore((state) => state.reset);
  const density = useUIStore((state) => state.density);

  const filteredSignals = sortSignals(
    signals.filter((signal) => {
      const matchesDirection = direction === "all" || signal.direction === direction;
      const matchesStatus = status === "all" || signal.status === status;
      const matchesPair = pair === "all" || signal.symbol === pair;

      return matchesDirection && matchesStatus && matchesPair;
    }),
    sort
  );

  return (
    <div className="space-y-4">
      <SignalFilters pairs={pairs} />
      <div className="grid gap-4">
        {filteredSignals.length > 0 ? (
          filteredSignals.map((signal) => (
            <SignalCard density={density} key={signal.id} signal={signal} />
          ))
        ) : (
          <div className="rounded-lg border border-dashed border-[#45536a] bg-[var(--panel)] p-8 text-center">
            <h3 className="text-lg font-semibold text-[#fff8df]">No signals match these filters</h3>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--muted)]">
              Adjust direction, status, or pair filters to bring more market setups back into
              view.
            </p>
            <Button className="mt-5" onClick={reset} variant="primary">
              Reset filters
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
