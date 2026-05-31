"use client";

import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { SlidersHorizontal, X } from "lucide-react";
import { z } from "zod";

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

const filterSchema = z.object({
  direction: z.enum(directions),
  status: z.enum(statuses),
  pair: z.string().min(1, "Choose a pair filter."),
  sort: z.enum(["confidence", "newest", "symbol"])
});

type SignalFilterFormValues = z.infer<typeof filterSchema>;

const defaultFilters: SignalFilterFormValues = {
  direction: "all",
  status: "all",
  pair: "all",
  sort: "confidence"
};

function readFiltersFromSearchParams(searchParams: URLSearchParams): SignalFilterFormValues {
  const candidate = {
    direction: searchParams.get("direction") ?? defaultFilters.direction,
    status: searchParams.get("status") ?? defaultFilters.status,
    pair: searchParams.get("pair") ?? defaultFilters.pair,
    sort: searchParams.get("sort") ?? defaultFilters.sort
  };
  const parsed = filterSchema.safeParse(candidate);

  return parsed.success ? parsed.data : defaultFilters;
}

function writeFiltersToSearchParams(values: SignalFilterFormValues): string {
  const nextParams = new URLSearchParams();

  if (values.direction !== defaultFilters.direction) {
    nextParams.set("direction", values.direction);
  }

  if (values.status !== defaultFilters.status) {
    nextParams.set("status", values.status);
  }

  if (values.pair !== defaultFilters.pair) {
    nextParams.set("pair", values.pair);
  }

  if (values.sort !== defaultFilters.sort) {
    nextParams.set("sort", values.sort);
  }

  return nextParams.toString();
}

export function SignalFilters({ pairs }: SignalFiltersProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const direction = useSignalStore((state) => state.direction);
  const status = useSignalStore((state) => state.status);
  const pair = useSignalStore((state) => state.pair);
  const sort = useSignalStore((state) => state.sort);
  const setDirection = useSignalStore((state) => state.setDirection);
  const setStatus = useSignalStore((state) => state.setStatus);
  const setPair = useSignalStore((state) => state.setPair);
  const setSort = useSignalStore((state) => state.setSort);
  const reset = useSignalStore((state) => state.reset);

  const form = useForm<SignalFilterFormValues>({
    defaultValues: readFiltersFromSearchParams(searchParams),
    mode: "onChange"
  });
  const values = useWatch({ control: form.control });

  useEffect(() => {
    form.reset(readFiltersFromSearchParams(searchParams));
  }, [form, searchParams]);

  useEffect(() => {
    const candidate = {
      direction: values.direction ?? direction,
      status: values.status ?? status,
      pair: values.pair ?? pair,
      sort: values.sort ?? sort
    };
    const parsed = filterSchema.safeParse(candidate);

    if (!parsed.success) {
      return;
    }

    setDirection(parsed.data.direction);
    setStatus(parsed.data.status);
    setPair(parsed.data.pair);
    setSort(parsed.data.sort);

    const nextQuery = writeFiltersToSearchParams(parsed.data);
    const currentQuery = searchParams.toString();

    if (nextQuery !== currentQuery) {
      router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
    }
  }, [
    direction,
    pathname,
    pair,
    router,
    searchParams,
    setDirection,
    setPair,
    setSort,
    setStatus,
    sort,
    status,
    values.direction,
    values.pair,
    values.sort,
    values.status
  ]);

  function resetFilters() {
    form.reset(defaultFilters);
    reset();
    router.replace(pathname, { scroll: false });
  }

  return (
    <form className="flex flex-col gap-4 rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] px-5 py-4 shadow-[var(--surface-shadow)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-[var(--gold)]" />
          <h2 className="text-base font-semibold text-[#fff8df]">Signal Queue</h2>
        </div>
        <Button onClick={resetFilters} size="sm" type="button" variant="ghost">
          <X className="h-4 w-4" />
          Reset
        </Button>
      </div>

      <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_180px]">
        <label className="grid gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Direction
          <select
            className="h-10 rounded-lg border border-[var(--panel-border)] bg-[#0d131c] px-3 text-sm font-medium normal-case tracking-normal text-[#fff8df] outline-none focus:border-[var(--gold)]"
            {...form.register("direction", {
              validate: (value) => filterSchema.shape.direction.safeParse(value).success
            })}
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
            {...form.register("status", {
              validate: (value) => filterSchema.shape.status.safeParse(value).success
            })}
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
            {...form.register("pair", {
              validate: (value) => filterSchema.shape.pair.safeParse(value).success
            })}
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
            {...form.register("sort", {
              validate: (value) => filterSchema.shape.sort.safeParse(value).success
            })}
          >
            {sorts.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </form>
  );
}
