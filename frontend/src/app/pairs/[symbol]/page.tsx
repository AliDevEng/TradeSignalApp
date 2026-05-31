import Link from "next/link";
import { ArrowLeft, BarChart3, Clock3, Layers3 } from "lucide-react";
import { notFound } from "next/navigation";

import { CandlestickChart } from "@/components/charts/CandlestickChart";
import { SignalBadge, SignalStatusBadge } from "@/components/signals/SignalBadge";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { formatDateTime, formatPercent } from "@/lib/formatters";
import { mapApiPair, mapApiSignal } from "@/lib/signalMappers";
import {
  getCandlesForPair,
  getSignalsForPair,
  getTradingPairBySymbol
} from "@/lib/mockSignals";
import { getPair, getPairSignals } from "@/services/tradeService";
import type { Signal, TradingPair } from "@/types/signal";

type PairDetailPageProps = {
  params: Promise<{
    symbol: string;
  }>;
};

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
  } catch {
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
  const candles = getCandlesForPair(pair.symbol);

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
          <CandlestickChart
            candles={candles}
            signal={activeSignal}
            subtitle="Recent price action with active signal execution levels layered directly on chart."
            title={`${pair.symbol} market structure`}
          />

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
