import { useQuery } from "@tanstack/react-query";

import { mapApiPositionSize } from "@/lib/riskMappers";
import { getPositionSize } from "@/services/riskService";
import type { Signal } from "@/types/signal";

/** Whether a signal can be sized at all: directional, with an entry and a stop. */
export function isSignalSizeable(signal: Signal): boolean {
  return signal.direction !== "neutral" && signal.entryPrice > 0 && signal.stopLoss !== null;
}

/**
 * Fetch the sized position for a signal against the given account inputs. Cached
 * per (signal, account inputs). The caller renders this only once the account is
 * configured and the signal is sizeable, so it has no `enabled` gate — keeping
 * React Query out of collapsed list cards entirely (no QueryClient needed there).
 */
export function usePositionSizeQuery(signal: Signal, balance: number, riskPercent: number) {
  const takeProfits = signal.targets.map((target) => target.price);

  return useQuery({
    queryKey: [
      "position-size",
      signal.id,
      balance,
      riskPercent,
      signal.entryPrice,
      signal.stopLoss,
      takeProfits
    ],
    queryFn: async () =>
      mapApiPositionSize(
        await getPositionSize({
          pair: signal.symbol,
          accountBalance: balance,
          riskPercent,
          entry: signal.entryPrice,
          // The caller guarantees a non-null stop (isSignalSizeable) before render.
          stopLoss: signal.stopLoss as number,
          takeProfits
        })
      ),
    staleTime: 5 * 60_000
  });
}
