"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams, type ReadonlyURLSearchParams } from "next/navigation";
import { z } from "zod";

import type { SignalListParams } from "@/services/tradeService";

/**
 * Signal-browse filters with the **URL as the single source of truth**. The
 * previous design synced a Zustand store *and* the URL in a feedback-prone
 * effect; here the query string is authoritative, so filters are shareable,
 * back/forward works, and the server query is derived directly from it — no
 * store, no double-write, no client-side refinement over partial pages.
 */
export type SignalFilterValues = {
  direction: "all" | "buy" | "sell" | "neutral";
  tradeStyle: "all" | "scalp" | "swing";
  status: "all" | "active" | "watchlist" | "expired";
  outcome: "all" | "open" | "win" | "loss" | "expired";
  /** "all" or a pair symbol. */
  pair: string;
  sort: "confidence" | "newest" | "symbol";
};

const filterSchema = z.object({
  direction: z.enum(["all", "buy", "sell", "neutral"]),
  tradeStyle: z.enum(["all", "scalp", "swing"]),
  status: z.enum(["all", "active", "watchlist", "expired"]),
  outcome: z.enum(["all", "open", "win", "loss", "expired"]),
  pair: z.string().min(1),
  sort: z.enum(["confidence", "newest", "symbol"])
});

export const DEFAULT_SIGNAL_FILTERS: SignalFilterValues = {
  direction: "all",
  tradeStyle: "all",
  status: "all",
  outcome: "all",
  pair: "all",
  sort: "confidence"
};

// URL param name per field. `style` is the tradeStyle (kept stable so existing
// deep links like /signals?status=active&sort=confidence keep working).
const PARAM: Record<keyof SignalFilterValues, string> = {
  direction: "direction",
  tradeStyle: "style",
  status: "status",
  outcome: "outcome",
  pair: "pair",
  sort: "sort"
};

const FILTER_KEYS = Object.keys(PARAM) as Array<keyof SignalFilterValues>;

export function parseSignalFilters(
  searchParams: URLSearchParams | ReadonlyURLSearchParams
): SignalFilterValues {
  const candidate = Object.fromEntries(
    FILTER_KEYS.map((key) => [key, searchParams.get(PARAM[key]) ?? DEFAULT_SIGNAL_FILTERS[key]])
  );
  const parsed = filterSchema.safeParse(candidate);
  return parsed.success ? parsed.data : DEFAULT_SIGNAL_FILTERS;
}

/** Map the UI filter values onto the server's signal-list query params. */
export function toSignalListParams(
  filters: SignalFilterValues
): Pick<SignalListParams, "pair" | "signalType" | "direction" | "status" | "result" | "sort"> {
  return {
    pair: filters.pair === "all" ? undefined : filters.pair,
    signalType: filters.tradeStyle === "all" ? undefined : filters.tradeStyle,
    direction: filters.direction === "all" ? undefined : filters.direction,
    status: filters.status === "all" ? undefined : filters.status,
    result: filters.outcome === "all" ? undefined : filters.outcome,
    sort: filters.sort
  };
}

export function useSignalFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters = useMemo(() => parseSignalFilters(searchParams), [searchParams]);

  const replace = useCallback(
    (next: URLSearchParams) => {
      const query = next.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router]
  );

  // Merge a partial change into the current filters, dropping params that are at
  // their default so the URL stays clean. Non-filter params (e.g. `run`) are
  // preserved untouched.
  const setFilters = useCallback(
    (patch: Partial<SignalFilterValues>) => {
      const merged = { ...filters, ...patch };
      const next = new URLSearchParams(searchParams.toString());
      for (const key of FILTER_KEYS) {
        if (merged[key] === DEFAULT_SIGNAL_FILTERS[key]) {
          next.delete(PARAM[key]);
        } else {
          next.set(PARAM[key], String(merged[key]));
        }
      }
      replace(next);
    },
    [filters, replace, searchParams]
  );

  // Clear only the filter params; anything else in the URL is left in place.
  const reset = useCallback(() => {
    const next = new URLSearchParams(searchParams.toString());
    for (const key of FILTER_KEYS) {
      next.delete(PARAM[key]);
    }
    replace(next);
  }, [replace, searchParams]);

  return { filters, setFilters, reset };
}
