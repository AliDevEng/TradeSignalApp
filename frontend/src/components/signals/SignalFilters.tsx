"use client";

import { SlidersHorizontal, X } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { useSignalStore, type SignalSort } from "@/store/signalStore";
import type { SignalDirection, SignalStatus, TradingPair } from "@/types/signal";

type SignalFiltersProps = {
  pairs: TradingPair[];
};

const directions: Array<"all" | SignalDirection> = ["all", "buy", "sell", "neutral"];
const statuses: Array<"all" | SignalStatus> = ["all", "active", "watchlist", "expired"];
const sorts: Array<{ label: string; value: SignalSort }> = [
  { label: "Confidence", value: "confidence" },
  { label: "Newest", value: "newest" },
  { label: "Symbol", value: "symbol" }
];

export function SignalFilters({ pairs }: SignalFiltersProps) {
  const direction = useSignalStore((state) => state.direction);
  const status = useSignalStore((state) => state.status);
  const pair = useSignalStore((state) => state.pair);
  const sort = useSignalStore((state) => state.sort);
  const setDirection = useSignalStore((state) => state.setDirection);
  const setStatus = useSignalStore((state) => state.setStatus);
  const setPair = useSignalStore((state) => state.setPair);
  const setSort = useSignalStore((state) => state.setSort);
  const reset = useSignalStore((state) => state.reset);

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] px-5 py-4 shadow-[var(--surface-shadow)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-[var(--gold)]" />
          <h2 className="text-base font-semibold text-[#fff8df]">Signal Queue</h2>
        </div>
        <Button onClick={reset} size="sm" variant="ghost">
          <X className="h-4 w-4" />
          Reset
        </Button>
      </div>

      <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_180px]">
        <label className="grid gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Direction
          <select
            className="h-10 rounded-lg border border-[var(--panel-border)] bg-[#0d131c] px-3 text-sm font-medium normal-case tracking-normal text-[#fff8df] outline-none focus:border-[var(--gold)]"
            onChange={(event) => setDirection(event.target.value as typeof direction)}
            value={direction}
          >
            {directions.map((item) => (
              <option key={item} value={item}>
                {item === "all" ? "All directions" : item.toUpperCase()}
              </option>
            ))}
          </select>
        </label>

        <label className="grid gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Status
          <select
            className="h-10 rounded-lg border border-[var(--panel-border)] bg-[#0d131c] px-3 text-sm font-medium normal-case tracking-normal text-[#fff8df] outline-none focus:border-[var(--gold)]"
            onChange={(event) => setStatus(event.target.value as typeof status)}
            value={status}
          >
            {statuses.map((item) => (
              <option key={item} value={item}>
                {item === "all" ? "All statuses" : item}
              </option>
            ))}
          </select>
        </label>

        <label className="grid gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Pair
          <select
            className="h-10 rounded-lg border border-[var(--panel-border)] bg-[#0d131c] px-3 text-sm font-medium normal-case tracking-normal text-[#fff8df] outline-none focus:border-[var(--gold)]"
            onChange={(event) => setPair(event.target.value)}
            value={pair}
          >
            <option value="all">All pairs</option>
            {pairs.map((item) => (
              <option key={item.symbol} value={item.symbol}>
                {item.symbol}
              </option>
            ))}
          </select>
        </label>

        <label className="grid gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Sort
          <select
            className="h-10 rounded-lg border border-[var(--panel-border)] bg-[#0d131c] px-3 text-sm font-medium normal-case tracking-normal text-[#fff8df] outline-none focus:border-[var(--gold)]"
            onChange={(event) => setSort(event.target.value as SignalSort)}
            value={sort}
          >
            {sorts.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}
