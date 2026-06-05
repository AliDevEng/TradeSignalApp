"use client";

import { X } from "lucide-react";
import { SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { useSignalFilters, type SignalFilterValues } from "@/hooks/useSignalFilters";
import type { TradingPair } from "@/types/signal";

type SignalFiltersProps = {
  pairs: TradingPair[];
};

const directions: Array<SignalFilterValues["direction"]> = ["all", "buy", "sell", "neutral"];
const tradeStyles: Array<SignalFilterValues["tradeStyle"]> = ["all", "scalp", "swing"];
const statuses: Array<SignalFilterValues["status"]> = ["all", "active", "watchlist", "expired"];
const outcomes: Array<SignalFilterValues["outcome"]> = ["all", "open", "win", "loss", "expired"];
const sorts: Array<{ label: string; value: SignalFilterValues["sort"] }> = [
  { label: "Confidence", value: "confidence" },
  { label: "Newest", value: "newest" },
  { label: "Symbol", value: "symbol" }
];

const outcomeLabels: Record<SignalFilterValues["outcome"], string> = {
  all: "All outcomes",
  open: "Open",
  win: "Wins",
  loss: "Losses",
  expired: "Expired"
};

const selectClass =
  "h-10 rounded-lg border border-[var(--panel-border)] bg-[#0d131c] px-3 text-sm font-medium normal-case tracking-normal text-[#fff8df] outline-none focus:border-[var(--gold)]";
const labelClass =
  "grid gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]";

function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

/**
 * Server-side signal filters. Every control reads from and writes to the URL via
 * {@link useSignalFilters}; the browse page derives its API query from the same
 * source, so the list, the count, and the sort are always consistent (no
 * client-side refinement over partially-loaded pages).
 */
export function SignalFilters({ pairs }: SignalFiltersProps) {
  const { filters, setFilters, reset } = useSignalFilters();

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] px-5 py-4 shadow-[var(--surface-shadow)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-[var(--gold)]" />
          <h2 className="text-base font-semibold text-[#fff8df]">Signal Queue</h2>
        </div>
        <Button onClick={reset} size="sm" type="button" variant="ghost">
          <X className="h-4 w-4" />
          Reset
        </Button>
      </div>

      <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_1fr_1fr_180px]">
        <label className={labelClass}>
          Direction
          <select
            className={selectClass}
            value={filters.direction}
            onChange={(event) =>
              setFilters({ direction: event.target.value as SignalFilterValues["direction"] })
            }
          >
            {directions.map((item) => (
              <option key={item} value={item}>
                {item === "all" ? "All directions" : item.toUpperCase()}
              </option>
            ))}
          </select>
        </label>

        <label className={labelClass}>
          Style
          <select
            className={selectClass}
            value={filters.tradeStyle}
            onChange={(event) =>
              setFilters({ tradeStyle: event.target.value as SignalFilterValues["tradeStyle"] })
            }
          >
            {tradeStyles.map((item) => (
              <option key={item} value={item}>
                {item === "all" ? "All styles" : titleCase(item)}
              </option>
            ))}
          </select>
        </label>

        <label className={labelClass}>
          Status
          <select
            className={selectClass}
            value={filters.status}
            onChange={(event) =>
              setFilters({ status: event.target.value as SignalFilterValues["status"] })
            }
          >
            {statuses.map((item) => (
              <option key={item} value={item}>
                {item === "all" ? "All statuses" : titleCase(item)}
              </option>
            ))}
          </select>
        </label>

        <label className={labelClass}>
          Outcome
          <select
            className={selectClass}
            value={filters.outcome}
            onChange={(event) =>
              setFilters({ outcome: event.target.value as SignalFilterValues["outcome"] })
            }
          >
            {outcomes.map((item) => (
              <option key={item} value={item}>
                {outcomeLabels[item]}
              </option>
            ))}
          </select>
        </label>

        <label className={labelClass}>
          Pair
          <select
            className={selectClass}
            value={filters.pair}
            onChange={(event) => setFilters({ pair: event.target.value })}
          >
            <option value="all">All pairs</option>
            {pairs.map((item) => (
              <option key={item.symbol} value={item.symbol}>
                {item.symbol}
              </option>
            ))}
          </select>
        </label>

        <label className={labelClass}>
          Sort
          <select
            className={selectClass}
            value={filters.sort}
            onChange={(event) =>
              setFilters({ sort: event.target.value as SignalFilterValues["sort"] })
            }
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
