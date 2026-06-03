import type { Signal } from "@/types/signal";
import type {
  SignalDirectionFilter,
  SignalSort,
  SignalStatusFilter,
  SignalTradeStyleFilter
} from "@/store/signalStore";

export type SignalRefinement = {
  direction: SignalDirectionFilter;
  tradeStyle: SignalTradeStyleFilter;
  status: SignalStatusFilter;
  /** "all" or a pair symbol. Applied client-side as a refinement. */
  pair: string;
  sort: SignalSort;
};

/** Client-side direction/style/status/pair refinement over an already-fetched set. */
export function filterSignals(signals: Signal[], refinement: SignalRefinement): Signal[] {
  return signals.filter((signal) => {
    const matchesDirection = refinement.direction === "all" || signal.direction === refinement.direction;
    const matchesStyle = refinement.tradeStyle === "all" || signal.tradeStyle === refinement.tradeStyle;
    const matchesStatus = refinement.status === "all" || signal.status === refinement.status;
    const matchesPair = refinement.pair === "all" || signal.symbol === refinement.pair;

    return matchesDirection && matchesStyle && matchesStatus && matchesPair;
  });
}

export function sortSignals(signals: Signal[], sort: SignalSort): Signal[] {
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

export function refineSignals(signals: Signal[], refinement: SignalRefinement): Signal[] {
  return sortSignals(filterSignals(signals, refinement), refinement.sort);
}
