"use client";

import { useMemo } from "react";

import { SignalCard } from "@/components/signals/SignalCard";
import { SignalFilters } from "@/components/signals/SignalFilters";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { refineSignals } from "@/lib/signalFilters";
import { useSignalStore } from "@/store/signalStore";
import { useUIStore } from "@/store/uiStore";
import type { Signal, TradingPair } from "@/types/signal";

type SignalListProps = {
  signals: Signal[];
  pairs: TradingPair[];
};

export function SignalList({ signals, pairs }: SignalListProps) {
  const direction = useSignalStore((state) => state.direction);
  const tradeStyle = useSignalStore((state) => state.tradeStyle);
  const status = useSignalStore((state) => state.status);
  const outcome = useSignalStore((state) => state.outcome);
  const pair = useSignalStore((state) => state.pair);
  const sort = useSignalStore((state) => state.sort);
  const reset = useSignalStore((state) => state.reset);
  const density = useUIStore((state) => state.density);

  const filteredSignals = useMemo(
    () => refineSignals(signals, { direction, tradeStyle, status, outcome, pair, sort }),
    [signals, direction, tradeStyle, status, outcome, pair, sort]
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
