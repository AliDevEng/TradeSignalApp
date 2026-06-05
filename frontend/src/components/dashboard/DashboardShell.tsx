"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  Clock3,
  Database,
  RefreshCw,
  ShieldAlert,
  Target,
  TimerReset,
  Zap
} from "lucide-react";

import { RelativeTime } from "@/components/common/RelativeTime";
import { HealthPanel } from "@/components/health/HealthPanel";
import { PipelineStatusBanner } from "@/components/signals/PipelineStatusBanner";
import { SignalList } from "@/components/signals/SignalList";
import { SignalListSkeleton } from "@/components/signals/SignalListSkeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import {
  useAnalysisRunsQuery,
  usePerformanceQuery,
  usePipelineStatusQuery,
  useSignalsQuery
} from "@/hooks/useTradeQueries";
import { PREVIEW_DATA_ENABLED } from "@/lib/env";
import { formatPercent, formatPrice, getPricePrecision } from "@/lib/formatters";
import { signals as mockSignals, tradingPairs } from "@/lib/mockSignals";
import { formatR } from "@/lib/outcome";
import type { Signal, TradingPair } from "@/types/signal";

const DASH = "-";
const emptyPairs: TradingPair[] = [];
const emptySignals: Signal[] = [];
const subscribeToHydration = () => () => undefined;

function formatProfitFactor(value: number | null | undefined): string {
  return value === null || value === undefined ? DASH : value.toFixed(2);
}

function formatRunLabel(run: { status: string; trigger: string; timeframe: string } | undefined) {
  if (!run) {
    return "Waiting for first run";
  }

  return `${run.status} ${run.trigger} run on ${run.timeframe}`;
}

export function DashboardShell() {
  const { pairsQuery, signalsQuery } = useSignalsQuery();
  const analysisRunsQuery = useAnalysisRunsQuery();
  const performanceQuery = usePerformanceQuery();
  const pipelineQuery = usePipelineStatusQuery();
  const hasMounted = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false
  );

  const apiError = hasMounted ? (pairsQuery.error ?? signalsQuery.error) : null;
  const showPreview = Boolean(apiError) && PREVIEW_DATA_ENABLED;

  const pairs: TradingPair[] = hasMounted
    ? (pairsQuery.data ?? (showPreview ? tradingPairs : emptyPairs))
    : emptyPairs;
  const signals: Signal[] = hasMounted
    ? (signalsQuery.data?.signals ?? (showPreview ? mockSignals : emptySignals))
    : emptySignals;
  const performance = hasMounted ? (performanceQuery.data ?? null) : null;
  const latestRun = hasMounted ? analysisRunsQuery.data?.data[0] : undefined;

  const isLoadingSignals =
    !hasMounted || ((pairsQuery.isLoading || signalsQuery.isLoading) && !signalsQuery.data);
  const monitoredPairs = pairs.filter((pair) => pair.isActive).length;
  const activeSignals = signals.filter((signal) => signal.status === "active").length;
  const openSignals = signals.filter((signal) => signal.outcome === "open").length;
  const unprotectedSignals = signals.filter(
    (signal) => signal.status === "active" && signal.stopLoss === null
  ).length;
  const averageConfidence =
    signals.length > 0
      ? signals.reduce((sum, signal) => sum + signal.confidence, 0) / signals.length
      : 0;

  const topSignal = [...signals].sort((a, b) => b.confidence - a.confidence)[0];
  const precision = topSignal ? getPricePrecision(topSignal.symbol) : 2;
  const cadenceMinutes = pipelineQuery.data?.interval_minutes ?? null;
  const cadenceLabel = cadenceMinutes !== null ? `${cadenceMinutes}m` : DASH;
  const overall = performance?.overall;
  const hasTrackRecord = (overall?.total ?? 0) > 0;
  const winRateLabel = hasTrackRecord ? formatPercent(overall!.winRate) : DASH;
  const profitFactorLabel = formatProfitFactor(overall?.profitFactor);
  const netRLabel = hasTrackRecord ? (formatR(overall!.totalR) ?? DASH) : DASH;

  const attentionItems = [
    apiError
      ? {
          label: showPreview ? "Live API unavailable - preview data active" : "Live API unavailable",
          tone: "danger" as const
        }
      : null,
    unprotectedSignals > 0
      ? { label: `${unprotectedSignals} active signal needs a stop`, tone: "warning" as const }
      : null,
    activeSignals === 0 ? { label: "No active setups in the current queue", tone: "neutral" as const } : null,
    !hasTrackRecord ? { label: "Track record starts after the first closed trade", tone: "neutral" as const } : null
  ].filter(Boolean) as Array<{ label: string; tone: "danger" | "warning" | "neutral" }>;

  function refreshMarketData() {
    void pairsQuery.refetch();
    void signalsQuery.refetch();
    void analysisRunsQuery.refetch();
    void performanceQuery.refetch();
    void pipelineQuery.refetch();
  }

  return (
    <div className="space-y-5">
      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-lg border border-[#2a3445] bg-[#0d131c] p-4 shadow-[var(--surface-shadow)] sm:p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <Badge className="border-[#244d7d] bg-[var(--blue-soft)] text-[var(--blue-strong)]">
                Live operations
              </Badge>
              <h1 className="mt-4 text-2xl font-semibold text-[#fff8df] sm:text-3xl">
                Dashboard
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[#b9c7d9]">
                Monitor active signals, model confidence, account performance, and backend health
                from one mobile-first workspace.
              </p>
            </div>
            <Button
              className="w-full sm:w-auto"
              disabled={pairsQuery.isFetching || signalsQuery.isFetching}
              onClick={refreshMarketData}
              type="button"
              variant="primary"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard icon={Activity} label="Active signals" value={activeSignals.toString()} />
            <StatCard
              icon={Target}
              label="Avg confidence"
              value={signals.length > 0 ? formatPercent(averageConfidence) : DASH}
            />
            <StatCard icon={Database} label="Pairs monitored" value={monitoredPairs.toString()} />
            <StatCard icon={TimerReset} label="Scan cadence" value={cadenceLabel} />
          </div>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-[var(--blue-strong)]" />
              <h2 className="font-semibold">Portfolio Pulse</h2>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Metric label="Win rate" value={winRateLabel} />
            <Metric label="Profit factor" value={profitFactorLabel} />
            <Metric label="Net R" value={netRLabel} />
            <Metric
              label="Closed trades"
              value={hasTrackRecord ? overall!.total.toString() : "0"}
            />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="min-w-0 overflow-hidden">
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-[var(--gold-strong)]" />
                <h2 className="font-semibold">Priority Setup</h2>
              </div>
              {topSignal ? (
                <Link
                  className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--blue-strong)] hover:text-[#8ab8ff]"
                  href={`/signals/${topSignal.id}`}
                >
                  Open signal
                  <ArrowUpRight className="h-4 w-4" />
                </Link>
              ) : null}
            </div>
          </CardHeader>
          <CardContent>
            {topSignal ? (
              <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_280px]">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-2xl font-semibold text-[#fff8df]">{topSignal.symbol}</h3>
                    <Badge tone={topSignal.direction === "buy" ? "success" : "neutral"}>
                      {topSignal.direction.toUpperCase()}
                    </Badge>
                    <Badge tone="info">{topSignal.tradeStyle}</Badge>
                    <Badge tone={topSignal.status === "active" ? "success" : "neutral"}>
                      {topSignal.status}
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm text-[var(--muted)]">{topSignal.displayName}</p>
                  <p className="mt-4 line-clamp-3 text-sm leading-6 text-[#c7d1df]">
                    {topSignal.rationale}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <ValueTile label="Confidence" value={formatPercent(topSignal.confidence)} />
                  <ValueTile
                    label="Open state"
                    value={topSignal.outcome === "open" ? "Open" : topSignal.outcome}
                  />
                  <ValueTile label="Entry" value={formatPrice(topSignal.entryPrice, precision)} />
                  <ValueTile
                    label="Stop"
                    value={topSignal.stopLoss ? formatPrice(topSignal.stopLoss, precision) : DASH}
                  />
                </div>
              </div>
            ) : (
              <p className="text-sm leading-6 text-[var(--muted)]">
                No signal is available yet. The feed will populate when the next scan returns a
                setup.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-[var(--gold)]" />
              <h2 className="font-semibold">Needs Attention</h2>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {attentionItems.length > 0 ? (
              attentionItems.map((item) => <AttentionItem item={item} key={item.label} />)
            ) : (
              <div className="flex items-start gap-3 rounded-lg border border-[#1f6f49] bg-[#092016] p-3">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#65d98d]" />
                <p className="text-sm leading-6 text-[#bfe6c8]">No operational issues detected.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Clock3 className="h-4 w-4 text-[var(--blue-strong)]" />
                <h2 className="font-semibold">Pipeline</h2>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <Metric label="Signals open" value={openSignals.toString()} />
              <Metric label="Latest run" value={formatRunLabel(latestRun)} />
              {signalsQuery.isSuccess ? (
                <RelativeTime
                  className="block text-xs font-medium text-[var(--muted)]"
                  intervalMs={5_000}
                  prefix="Auto-refreshing - updated"
                  value={signalsQuery.dataUpdatedAt}
                />
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-[var(--blue-strong)]" />
                <h2 className="font-semibold">API Health</h2>
              </div>
            </CardHeader>
            <CardContent>
              <HealthPanel compact />
            </CardContent>
          </Card>
        </div>

        <section className="min-w-0 space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-[#fff8df]">Signal Queue</h2>
              <p className="mt-1 text-sm text-[var(--muted)]">
                Filtered live setups with risk, targets, and model reasoning.
              </p>
            </div>
          </div>

          <PipelineStatusBanner />

          {apiError ? (
            <ErrorState
              error={apiError}
              onRetry={refreshMarketData}
              title={showPreview ? "Live API unavailable, showing preview data" : "Live API unavailable"}
            />
          ) : null}

          {isLoadingSignals ? (
            <SignalListSkeleton />
          ) : (
            <SignalList pairs={pairs} signals={signals} />
          )}
        </section>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm text-[var(--muted)]">{label}</span>
      <span className="max-w-[60%] text-right text-sm font-semibold capitalize text-[#fff8df]">
        {value}
      </span>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value
}: {
  icon: typeof Activity;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-[#263247] bg-[#111722] p-4">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        <Icon className="h-4 w-4 text-[var(--gold-strong)]" />
        {label}
      </div>
      <p className="mt-3 text-2xl font-semibold text-[#fff8df]">{value}</p>
    </div>
  );
}

function ValueTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-[#263247] bg-[#101722] p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="mt-2 truncate text-lg font-semibold text-[#fff8df]">{value}</p>
    </div>
  );
}

function AttentionItem({
  item
}: {
  item: { label: string; tone: "danger" | "warning" | "neutral" };
}) {
  const toneClass = {
    danger: "border-[#6e2029] bg-[var(--red-soft)] text-[#ffb4b8]",
    warning: "border-[#6f5620] bg-[#191407] text-[#f2d48c]",
    neutral: "border-[#263247] bg-[#101722] text-[#b9c7d9]"
  }[item.tone];

  return (
    <div className={`rounded-lg border p-3 text-sm leading-6 ${toneClass}`}>{item.label}</div>
  );
}
