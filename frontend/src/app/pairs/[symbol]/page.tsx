import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, BarChart3, Clock3, Layers3 } from "lucide-react";
import { notFound } from "next/navigation";

import { SignalLevelMap } from "@/components/charts/SignalLevelMap";
import { SignalBadge, SignalStatusBadge } from "@/components/signals/SignalBadge";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PREVIEW_DATA_ENABLED } from "@/lib/env";
import { formatDateTime, formatPercent } from "@/lib/formatters";
import { mapApiPair, mapApiSignal } from "@/lib/signalMappers";
import { getSignalsForPair, getTradingPairBySymbol } from "@/lib/mockSignals";
import { ApiClientError } from "@/services/api";
import { getPair, getPairSignals } from "@/services/tradeService";
import type { Signal, TradingPair } from "@/types/signal";

type PairDetailPageProps = {
  params: Promise<{
    symbol: string;
  }>;
};

export async function generateMetadata({ params }: PairDetailPageProps): Promise<Metadata> {
  const { symbol } = await params;
  const upper = symbol.toUpperCase();

  return {
    title: upper,
    description: `Execution map, indicator context, and signal queue for ${upper}.`
  };
}

type PairDetailData = {
  pair: TradingPair;
  signals: Signal[];
};

async function loadPairDetail(symbol: string): Promise<PairDetailData | null> {
  try {
    const apiPair = await getPair(symbol);
    const pair = mapApiPair(apiPair);
    const apiSignals = await getPairSignals(pair.symbol);

    return {
      pair,
      signals: apiSignals.map((signal) => mapApiSignal(signal, [pair]))
    };
  } catch (error) {
    // Genuine 404 → the pair doesn't exist → not-found.
    if (error instanceof ApiClientError && error.status === 404) {
      return null;
    }
    // API down: only fall back to sample data in preview mode; otherwise let
    // the route error boundary handle it rather than showing fabricated data.
    if (!PREVIEW_DATA_ENABLED) {
      throw error;
    }
    const pair = getTradingPairBySymbol(symbol);
    if (!pair) {
      return null;
    }
    return {
      pair,
      signals: getSignalsForPair(pair.symbol)
    };
  }
}

export default async function PairDetailPage({ params }: PairDetailPageProps) {
  const { symbol } = await params;
  const data = await loadPairDetail(symbol);

  if (!data) {
    notFound();
  }

  const { pair, signals: pairSignals } = data;
  const activeSignal = pairSignals.find((signal) => signal.status === "active") ?? pairSignals[0];

  return (
    <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link
              className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--blue-strong)] transition-colors hover:text-[#8ab8ff]"
              href="/"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to dashboard
            </Link>
            <h1 className="mt-4 text-3xl font-semibold text-[#fff8df]">{pair.symbol}</h1>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{pair.displayName}</p>
          </div>

          <div className="rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
              Pair Status
            </p>
            <p className="mt-2 text-base font-semibold text-[#fff8df]">
              {pair.isActive ? "Monitored live" : "Archived from live rotation"}
            </p>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.35fr_0.95fr]">
          {activeSignal ? (
            <SignalLevelMap
              signal={activeSignal}
              subtitle="Active signal execution levels mapped against indicator reference levels for this pair."
              title={`${pair.symbol} market structure`}
            />
          ) : (
            <EmptyState
              description="No signal has been generated for this pair yet, so there is no execution map to render."
              title="Awaiting first signal"
            />
          )}

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-[var(--gold)]" />
                  <h2 className="text-lg font-semibold text-[#fff8df]">Pair Snapshot</h2>
                </div>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2">
                <PairMetric label="Signals tracked" value={pairSignals.length.toString()} />
                <PairMetric
                  label="Average confidence"
                  value={
                    pairSignals.length > 0
                      ? formatPercent(
                          pairSignals.reduce((sum, signal) => sum + signal.confidence, 0) /
                            pairSignals.length
                        )
                      : "0%"
                  }
                />
                <PairMetric
                  label="Current timeframe"
                  value={activeSignal?.timeframe ?? "Pending"}
                />
                <PairMetric
                  label="Last update"
                  value={activeSignal ? formatDateTime(activeSignal.generatedAt) : "Pending"}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Layers3 className="h-4 w-4 text-[var(--blue-strong)]" />
                  <h2 className="text-lg font-semibold text-[#fff8df]">Signal Queue</h2>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {pairSignals.length > 0 ? (
                  pairSignals.map((signal) => (
                    <Link
                      className="block rounded-lg border border-[var(--panel-border)] bg-[#0d131c] p-4 transition-colors hover:border-[#6f5620]"
                      href={`/signals/${signal.id}`}
                      key={signal.id}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <SignalBadge direction={signal.direction} />
                            <SignalStatusBadge status={signal.status} />
                          </div>
                          <p className="mt-3 text-sm leading-6 text-[#c2cad6]">
                            {signal.rationale}
                          </p>
                        </div>
                        <div className="text-right text-xs font-medium text-[var(--muted)]">
                          <div className="inline-flex items-center gap-1.5">
                            <Clock3 className="h-3.5 w-3.5" />
                            {formatDateTime(signal.generatedAt)}
                          </div>
                          <p className="mt-2 text-sm font-semibold text-[#fff8df]">
                            Confidence {formatPercent(signal.confidence)}
                          </p>
                        </div>
                      </div>
                    </Link>
                  ))
                ) : (
                  <div className="rounded-lg border border-dashed border-[#45536a] bg-[#0d131c] p-6 text-center text-sm text-[var(--muted)]">
                    No signals are available for this pair yet.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
    </div>
  );
}

function PairMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--panel-border)] bg-[#0d131c] p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="mt-3 text-base font-semibold text-[#fff8df]">{value}</p>
    </div>
  );
}
