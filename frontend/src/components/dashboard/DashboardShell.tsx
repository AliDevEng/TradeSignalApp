"use client";

import { BarChart3, Bot, Layers3, LineChart, RefreshCw, Sparkles } from "lucide-react";

import { RelativeTime } from "@/components/common/RelativeTime";
import { HealthPanel } from "@/components/health/HealthPanel";
import { SignalList } from "@/components/signals/SignalList";
import { SignalListSkeleton } from "@/components/signals/SignalListSkeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAnalysisRunsQuery, useSignalsQuery } from "@/hooks/useTradeQueries";
import { formatCompactNumber, formatPercent } from "@/lib/formatters";
import {
  signals as mockSignals,
  signalStats as mockSignalStats,
  tradingPairs
} from "@/lib/mockSignals";
import { useUIStore } from "@/store/uiStore";
import type { Signal, SignalStats, TradingPair } from "@/types/signal";

const intelligenceItems = [
  {
    label: "Market scan",
    value: "3 active pairs",
    tone: "success"
  },
  {
    label: "Provider mode",
    value: "AI ready",
    tone: "info"
  },
  {
    label: "Scheduler",
    value: "15 min cadence",
    tone: "neutral"
  }
] as const;

export function DashboardShell() {
  const { pairsQuery, signalsQuery } = useSignalsQuery();
  const analysisRunsQuery = useAnalysisRunsQuery();
  const density = useUIStore((state) => state.density);
  const setDensity = useUIStore((state) => state.setDensity);

  const pairs = pairsQuery.data ?? tradingPairs;
  const signals = signalsQuery.data?.signals ?? mockSignals;
  const stats = calculateSignalStats(signals, pairs);
  const latestRun = analysisRunsQuery.data?.data[0];
  const isLoadingSignals = (pairsQuery.isLoading || signalsQuery.isLoading) && !signalsQuery.data;
  const apiError = pairsQuery.error ?? signalsQuery.error;
  const isPreviewData = Boolean(apiError);

  function refreshMarketData() {
    void pairsQuery.refetch();
    void signalsQuery.refetch();
    void analysisRunsQuery.refetch();
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
      <section className="space-y-5 xl:col-span-2">
        <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
          <section className="overflow-hidden rounded-lg border border-[#6f5620] bg-[#0b0d12] p-6 text-white shadow-[0_24px_80px_rgba(0,0,0,0.48)]">
            <div className="flex flex-wrap items-start justify-between gap-5">
              <div className="max-w-2xl">
                <Badge className="border-[#6f5620] bg-[#191407] text-[var(--gold-strong)]">
                  Premium market intelligence
                </Badge>
                <h1 className="mt-5 max-w-3xl text-3xl font-semibold tracking-normal text-[#fff8df] sm:text-4xl">
                  Luxury-grade command center for AI-assisted market execution
                </h1>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-[#c2cad6] sm:text-base">
                  Scan conviction, risk, and operational health in one high-contrast workspace
                  built for fast decisions.
                </p>
                <div className="mt-6 grid gap-3 sm:grid-cols-3">
                  <HeroPill label="Conviction" value={formatPercent(stats.averageConfidence)} />
                  <HeroPill label="Model edge" value={formatPercent(stats.modelWinRate)} />
                  <HeroPill label="Live setups" value={stats.activeSignals.toString()} />
                </div>
              </div>
              <Button
                disabled={pairsQuery.isFetching || signalsQuery.isFetching}
                onClick={refreshMarketData}
                type="button"
                variant="primary"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh view
              </Button>
            </div>
          </section>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-[var(--blue-strong)]" />
                <h2 className="font-semibold">Portfolio Pulse</h2>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <Metric label="Active signals" value={stats.activeSignals.toString()} />
              <Metric label="Average confidence" value={formatPercent(stats.averageConfidence)} />
              <Metric label="Model win rate" value={formatPercent(stats.modelWinRate)} />
              <div className="border-t border-[var(--panel-border)] pt-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-[var(--muted)]">Capital posture</span>
                  <Badge tone="success">Controlled</Badge>
                </div>
                <div className="mt-4 space-y-3">
                  <PulseBar label="Conviction" tone="gold" value={73} />
                  <PulseBar label="Exposure" tone="blue" value={42} />
                  <PulseBar label="Risk load" tone="red" value={28} />
                </div>
              </div>
              <div className="rounded-lg border border-[#244d7d] bg-[var(--blue-soft)] p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-[var(--blue-strong)]">
                  <LineChart className="h-4 w-4" />
                  Next decision window
                </div>
                <p className="mt-2 text-sm leading-6 text-[#b9c7d9]">
                  Re-score active setups after the next 1h candle closes.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Monitored pairs" value={stats.monitoredPairs.toString()} />
          <StatCard label="Analysis cadence" value={`${stats.analysisCadenceMinutes}m`} />
          <StatCard
            label="Monthly signal volume"
            value={formatCompactNumber(stats.monthlySignalVolume)}
          />
          <StatCard label="UI density" value={density} />
        </div>

        <div className="grid gap-5 xl:grid-cols-[280px_1fr]">
          <aside className="space-y-5">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4 text-[var(--gold)]" />
                  <h2 className="font-semibold">Signal Engine</h2>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {intelligenceItems.map((item) => (
                  <div className="flex items-center justify-between gap-3" key={item.label}>
                    <span className="text-sm text-[var(--muted)]">{item.label}</span>
                    <Badge tone={item.tone}>{item.value}</Badge>
                  </div>
                ))}
                <div className="rounded-lg border border-[#6f5620] bg-[#120f09] p-4 text-[#fff8df]">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Sparkles className="h-4 w-4 text-[var(--gold-strong)]" />
                    Model focus
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[#c7b98d]">
                    {latestRun
                      ? `Latest ${latestRun.trigger} run is ${latestRun.status} on ${latestRun.timeframe}.`
                      : "Prioritize high-confidence continuation setups and protect capital during balanced regimes."}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Layers3 className="h-4 w-4 text-[var(--blue-strong)]" />
                  <h2 className="font-semibold">API Health</h2>
                </div>
              </CardHeader>
              <CardContent>
                <HealthPanel compact />
              </CardContent>
            </Card>
          </aside>

          <section className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-[#fff8df]">Execution Feed</h2>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  Prioritized signals, risk levels, and model confidence.
                </p>
                {signalsQuery.isSuccess ? (
                  <RelativeTime
                    className="mt-1 block text-xs font-medium text-[var(--muted)]"
                    intervalMs={5_000}
                    prefix="Auto-refreshing · updated"
                    value={signalsQuery.dataUpdatedAt}
                  />
                ) : null}
              </div>
              <DensitySwitch density={density} setDensity={setDensity} />
            </div>

            {isPreviewData && apiError ? (
              <ErrorState
                error={apiError}
                onRetry={refreshMarketData}
                title="Live API unavailable, showing preview data"
              />
            ) : null}

            {isLoadingSignals ? (
              <SignalListSkeleton />
            ) : (
              <SignalList pairs={pairs} signals={signals} />
            )}
          </section>
        </div>
      </section>
    </div>
  );
}

function calculateSignalStats(signals: Signal[], pairs: TradingPair[]): SignalStats {
  if (signals.length === 0) {
    return {
      ...mockSignalStats,
      activeSignals: 0,
      averageConfidence: 0,
      monitoredPairs: pairs.filter((pair) => pair.isActive).length,
      monthlySignalVolume: 0
    };
  }

  return {
    activeSignals: signals.filter((signal) => signal.status === "active").length,
    averageConfidence: signals.reduce((sum, signal) => sum + signal.confidence, 0) / signals.length,
    modelWinRate: mockSignalStats.modelWinRate,
    monitoredPairs: pairs.filter((pair) => pair.isActive).length,
    analysisCadenceMinutes: mockSignalStats.analysisCadenceMinutes,
    monthlySignalVolume: Math.max(signals.length * 320, signals.length)
  };
}

function DensitySwitch({
  density,
  setDensity
}: {
  density: "comfortable" | "compact";
  setDensity: (density: "comfortable" | "compact") => void;
}) {
  return (
    <div
      aria-label="Feed density"
      className="flex rounded-lg border border-[var(--panel-border)] bg-[#111722] p-1"
      role="group"
    >
      <button
        aria-pressed={density === "comfortable"}
        className={`h-9 rounded-md px-3 text-sm font-semibold ${
          density === "comfortable" ? "bg-[var(--gold)] text-[#080a0f]" : "text-[var(--muted)]"
        }`}
        onClick={() => setDensity("comfortable")}
        type="button"
      >
        Comfortable
      </button>
      <button
        aria-pressed={density === "compact"}
        className={`h-9 rounded-md px-3 text-sm font-semibold ${
          density === "compact" ? "bg-[var(--gold)] text-[#080a0f]" : "text-[var(--muted)]"
        }`}
        onClick={() => setDensity("compact")}
        type="button"
      >
        Compact
      </button>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm text-[var(--muted)]">{label}</span>
      <span className="text-lg font-semibold text-[#fff8df]">{value}</span>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent>
        <p className="text-sm font-medium text-[var(--muted)]">{label}</p>
        <p className="mt-3 text-3xl font-semibold capitalize text-[#fff8df]">{value}</p>
      </CardContent>
    </Card>
  );
}

function PulseBar({
  label,
  tone,
  value
}: {
  label: string;
  tone: "gold" | "blue" | "red";
  value: number;
}) {
  const colorClass = {
    gold: "bg-[var(--gold)]",
    blue: "bg-[var(--blue)]",
    red: "bg-[var(--red)]"
  }[tone];

  return (
    <div>
      <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide">
        <span className="text-[#7f8da3]">{label}</span>
        <span className="text-[#fff8df]">{value}%</span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-[#0b111b]">
        <div className={`h-2 rounded-full ${colorClass}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function HeroPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[#2d3647] bg-[#111722] px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-[#7f8da3]">{label}</p>
      <p className="mt-1 text-xl font-semibold text-[var(--gold-strong)]">{value}</p>
    </div>
  );
}
