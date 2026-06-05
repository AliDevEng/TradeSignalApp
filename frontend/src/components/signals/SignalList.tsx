"use client";

import { useMemo } from "react";

import { SignalCard } from "@/components/signals/SignalCard";
import { SignalFilters } from "@/components/signals/SignalFilters";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { useSignalFilters } from "@/hooks/useSignalFilters";
import { refineSignals } from "@/lib/signalFilters";
import type { Signal, TradingPair } from "@/types/signal";

type SignalListProps = {
  signals: Signal[];
  pairs: TradingPair[];
};

export function SignalList({ signals, pairs }: SignalListProps) {
  const { filters, reset } = useSignalFilters();

  const filteredSignals = useMemo(
    () => refineSignals(signals, filters),
    [signals, filters]
  );

  return (
    <div className="space-y-4">
      <SignalFilters pairs={pairs} />
      <div className="grid gap-4">
        {filteredSignals.length > 0 ? (
          filteredSignals.map((signal) => (
            <SignalCard density="comfortable" key={signal.id} signal={signal} />
          ))
        ) : (
          <EmptyState
            action={
              <Button onClick={reset} variant="primary">
                Reset filters
              </Button>
            }
            description="Adjust direction, status, or pair filters to bring more market setups back into view."
            title="No signals match these filters"
          />
        )}
      </div>
    </div>
  );
}
