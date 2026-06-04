"use client";

import { useMemo, useSyncExternalStore } from "react";
import { RefreshCw } from "lucide-react";

import { RelativeTime } from "@/components/common/RelativeTime";
import { SignalCard } from "@/components/signals/SignalCard";
import { SignalListSkeleton } from "@/components/signals/SignalListSkeleton";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { useInfiniteSignalsQuery } from "@/hooks/useTradeQueries";
import { formatR, isClosedOutcome, outcomeCategory } from "@/lib/outcome";
import { signals as mockSignals } from "@/lib/mockSignals";
import { useUIStore } from "@/store/uiStore";
import type { Signal } from "@/types/signal";

const emptySignals: Signal[] = [];
const subscribeToHydration = () => () => undefined;

function closedAtTime(signal: Signal): number {
  return new Date(signal.closedAt ?? signal.generatedAt).getTime();
}

type ClosedSummary = {
  total: number;
  wins: number;
  losses: number;
  expired: number;
  netR: number;
  winRate: number | null;
};

/** A track-record summary derived purely from the loaded closed signals. */
function summarise(signals: Signal[]): ClosedSummary {
  let wins = 0;
  let losses = 0;
  let expired = 0;
  let netR = 0;

  for (const signal of signals) {
    const category = outcomeCategory(signal.outcome);
    if (category === "win") {
      wins += 1;
    } else if (category === "loss") {
      losses += 1;
    } else if (category === "expired") {
      expired += 1;
    }
    netR += signal.realizedR ?? 0;
  }

  const decided = wins + losses;
  return {
    total: signals.length,
    wins,
    losses,
    expired,
    netR,
    winRate: decided > 0 ? wins / decided : null
  };
}

export function ClosedSignalsPage() {
  const query = useInfiniteSignalsQuery();
  const density = useUIStore((state) => state.density);
  const hasMounted = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false
  );

  const isQueryError = hasMounted && query.isError;
  const sourceSignals = isQueryError ? mockSignals : hasMounted ? query.signals : emptySignals;

  const closedSignals = useMemo(
    () =>
      sourceSignals
        .filter((signal) => isClosedOutcome(signal.outcome))
        .sort((first, second) => closedAtTime(second) - closedAtTime(first)),
    [sourceSignals]
  );
  const summary = useMemo(() => summarise(closedSignals), [closedSignals]);

  const isInitialLoading = !hasMounted || (query.isLoading && !query.isError);

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-[#fff8df]">Closed Signals</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            The track record: every signal price has resolved — take-profit, stop, or expiry — with
            its realised R. Distinct from the active queue on the Signals page.
          </p>
        </div>
        <Button
          disabled={!hasMounted || query.isFetching}
          onClick={() => void query.refetch()}
          variant="primary"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {!isInitialLoading && closedSignals.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryStat label="Closed" value={String(summary.total)} />
          <SummaryStat
            label="Win rate"
            tone="win"
            value={summary.winRate !== null ? `${Math.round(summary.winRate * 100)}%` : "—"}
          />
          <SummaryStat label="Wins / Losses" value={`${summary.wins} / ${summary.losses}`} />
          <SummaryStat
            label="Net R"
            tone={summary.netR >= 0 ? "win" : "loss"}
            value={formatR(summary.netR) ?? "0.00R"}
          />
        </div>
      ) : null}

      {isQueryError ? (
        <ErrorState
          error={query.error as Error}
          onRetry={() => void query.refetch()}
          title="Live API unavailable, showing preview data"
        />
      ) : null}

      {hasMounted && !isQueryError && query.isSuccess ? (
        <p className="text-xs font-medium text-[var(--muted)]">
          <RelativeTime prefix="updated" value={query.dataUpdatedAt} intervalMs={5_000} />
        </p>
      ) : null}

      {isInitialLoading ? (
        <SignalListSkeleton />
      ) : closedSignals.length > 0 ? (
        <div className="grid gap-4">
          {closedSignals.map((signal) => (
            <SignalCard density={density} key={signal.id} signal={signal} />
          ))}
        </div>
      ) : (
        <EmptyState
          description="No signals have closed yet. Once price hits a target, stop, or a signal expires, it lands here with its realised R."
          title="No closed signals yet"
        />
      )}

      {query.hasNextPage && !query.isError ? (
        <div className="flex justify-center">
          <Button
            disabled={query.isFetchingNextPage}
            onClick={() => void query.fetchNextPage()}
            variant="secondary"
          >
            {query.isFetchingNextPage ? "Loading…" : "Load more"}
          </Button>
        </div>
      ) : null}
    </section>
  );
}

type SummaryStatProps = {
  label: string;
  value: string;
  tone?: "default" | "win" | "loss";
};

function SummaryStat({ label, value, tone = "default" }: SummaryStatProps) {
  const valueClass =
    tone === "win"
      ? "text-[#7bea9b]"
      : tone === "loss"
        ? "text-[var(--red-strong)]"
        : "text-[#fff8df]";

  return (
    <div className="rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] px-4 py-3 shadow-[var(--surface-shadow)]">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${valueClass}`}>{value}</p>
    </div>
  );
}
