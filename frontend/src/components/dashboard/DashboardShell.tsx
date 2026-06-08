"use client";

import { useSyncExternalStore } from "react";
import {
  Activity,
  CheckCircle2,
  Layers,
  LineChart,
  RefreshCw,
  ShieldAlert,
  Target,
  TrendingUp
} from "lucide-react";

import { EconomicCalendarBanner } from "@/components/calendar/EconomicCalendarBanner";
import { EconomicEventStrip } from "@/components/calendar/EconomicEventStrip";
import { HeroSetup } from "@/components/dashboard/HeroSetup";
import { AccountRiskCard } from "@/components/risk/AccountRiskCard";
import { PipelineStatusBanner } from "@/components/signals/PipelineStatusBanner";
import { SignalList } from "@/components/signals/SignalList";
import { SignalListSkeleton } from "@/components/signals/SignalListSkeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { usePerformanceQuery, useSignalsQuery } from "@/hooks/useTradeQueries";
import { PREVIEW_DATA_ENABLED } from "@/lib/env";
import { formatPercent } from "@/lib/formatters";
import { signals as mockSignals, tradingPairs } from "@/lib/mockSignals";
import { formatR } from "@/lib/outcome";
import type { Signal, TradingPair } from "@/types/signal";

const DASH = "-";
const emptyPairs: TradingPair[] = [];
const emptySignals: Signal[] = [];
const subscribeToHydration = () => () => undefined;

export function DashboardShell() {
  const { pairsQuery, signalsQuery } = useSignalsQuery();
  const performanceQuery = usePerformanceQuery();
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

  const isLoadingSignals =
    !hasMounted || ((pairsQuery.isLoading || signalsQuery.isLoading) && !signalsQuery.data);
  const activeSignals = signals.filter((signal) => signal.status === "active").length;
  const openSignals = signals.filter((signal) => signal.outcome === "open").length;
  const unprotectedSignals = signals.filter(
    (signal) => signal.status === "active" && signal.stopLoss === null
  ).length;
  const averageConfidence =
    signals.length > 0
      ? signals.reduce((sum, signal) => sum + signal.confidence, 0) / signals.length
      : 0;

  // Hero = the highest-conviction *active* setup; fall back to the best of any
  // status so the dashboard never leads with a blank slot when setups exist.
  const rankable = [...signals].sort((a, b) => b.confidence - a.confidence);
  const topSignal = rankable.find((signal) => signal.status === "active") ?? rankable[0];

  const overall = performance?.overall;
  const hasTrackRecord = (overall?.total ?? 0) > 0;
  const winRateLabel = hasTrackRecord ? formatPercent(overall!.winRate) : DASH;
  const netRLabel = hasTrackRecord ? (formatR(overall!.totalR) ?? DASH) : DASH;

  const attentionItems = [
    apiError
      ? {
          label: showPreview ? "Live API unavailable — preview data active" : "Live API unavailable",
          tone: "danger" as const
        }
      : null,
    unprotectedSignals > 0
      ? { label: `${unprotectedSignals} active signal needs a stop`, tone: "warning" as const }
      : null,
    activeSignals === 0
      ? { label: "No active setups in the current queue", tone: "neutral" as const }
      : null,
    !hasTrackRecord
      ? { label: "Track record starts after the first closed trade", tone: "neutral" as const }
      : null
  ].filter(Boolean) as Array<{ label: string; tone: "danger" | "warning" | "neutral" }>;

  function refreshMarketData() {
    void pairsQuery.refetch();
    void signalsQuery.refetch();
    void performanceQuery.refetch();
  }

  return (
    <div className="space-y-5">
      <EconomicCalendarBanner />
      <EconomicEventStrip />

      {/* Decision-first hero + live account control */}
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="min-w-0">
          {topSignal ? (
            <HeroSetup signal={topSignal} />
          ) : (
            <Card className="flex h-full min-h-[260px] flex-col items-center justify-center p-8 text-center">
              <Target className="h-8 w-8 text-[var(--muted)]" />
              <p className="mt-3 text-lg font-semibold text-[#fff8df]">No live setup yet</p>
              <p className="mt-1 max-w-sm text-sm text-[var(--muted)]">
                The feed populates the moment the next market scan returns a setup. Lot sizing and
                risk are ready the instant it lands.
              </p>
              <Button className="mt-4" onClick={refreshMarketData} variant="secondary">
                <RefreshCw className="h-4 w-4" />
                Refresh
              </Button>
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <AccountRiskCard signals={signals} />
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-[var(--gold)]" />
                <h2 className="font-semibold">Needs attention</h2>
              </div>
            </CardHeader>
            <CardContent className="space-y-2.5">
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
        </div>
      </section>

      {/* Trader KPI strip */}
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
        <Kpi icon={Activity} label="Active signals" value={activeSignals.toString()} />
        <Kpi
          icon={Target}
          label="Avg confidence"
          value={signals.length > 0 ? formatPercent(averageConfidence) : DASH}
        />
        <Kpi icon={Layers} label="Open trades" value={openSignals.toString()} />
        <Kpi icon={LineChart} label="Win rate" value={winRateLabel} />
        <Kpi icon={TrendingUp} label="Net R" value={netRLabel} />
      </section>

      {/* Full-width signal queue */}
      <section className="min-w-0 space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-[#fff8df]">Signal queue</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Every live setup with risk, targets, sizing, and model reasoning.
            </p>
          </div>
          <Button
            disabled={pairsQuery.isFetching || signalsQuery.isFetching}
            onClick={refreshMarketData}
            variant="secondary"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>

        <PipelineStatusBanner />

        {apiError ? (
          <ErrorState
            error={apiError}
            onRetry={refreshMarketData}
            title={
              showPreview ? "Live API unavailable, showing preview data" : "Live API unavailable"
            }
          />
        ) : null}

        {isLoadingSignals ? <SignalListSkeleton /> : <SignalList pairs={pairs} signals={signals} />}
      </section>
    </div>
  );
}

function Kpi({
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
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
        <Icon className="h-4 w-4 text-[var(--gold-strong)]" />
        {label}
      </div>
      <p className="mt-2.5 text-2xl font-bold text-[#fff8df]">{value}</p>
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

  return <div className={`rounded-lg border p-3 text-sm leading-6 ${toneClass}`}>{item.label}</div>;
}
