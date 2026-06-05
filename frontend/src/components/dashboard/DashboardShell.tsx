"use client";

import { BarChart3, Bot, Clock3, Layers3, RefreshCw, Sparkles } from "lucide-react";

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
import { formatPercent } from "@/lib/formatters";
import { signals as mockSignals, tradingPairs } from "@/lib/mockSignals";
import { formatR } from "@/lib/outcome";
import { useUIStore } from "@/store/uiStore";
import type { Signal, TradingPair } from "@/types/signal";

const DASH = "—";

function formatProfitFactor(value: number | null | undefined): string {
  return value === null || value === undefined ? DASH : value.toFixed(2);
}

export function DashboardShell() {
  const { pairsQuery, signalsQuery } = useSignalsQuery();
  const analysisRunsQuery = useAnalysisRunsQuery();
  const performanceQuery = usePerformanceQuery();
  const pipelineQuery = usePipelineStatusQuery();
  const density = useUIStore((state) => state.density);
  const setDensity = useUIStore((state) => state.setDensity);

  const apiError = pairsQuery.error ?? signalsQuery.error;
  // Only show bundled sample data when preview mode is explicitly enabled —
  // otherwise the dashboard reflects real state (empty until the API responds).
  const showPreview = Boolean(apiError) && PREVIEW_DATA_ENABLED;

  const pairs: TradingPair[] = pairsQuery.data ?? (showPreview ? tradingPairs : []);
  const signals: Signal[] = signalsQuery.data?.signals ?? (showPreview ? mockSignals : []);
  const performance = performanceQuery.data ?? null;

  const isLoadingSignals = (pairsQuery.isLoading || signalsQuery.isLoading) && !signalsQuery.data;
  const latestRun = analysisRunsQuery.data?.data[0];

  // ── Real, derived metrics (no fabricated numbers) ───────────────────────────
  const monitoredPairs = pairs.filter((pair) => pair.isActive).length;
  const activeSignals = signals.filter((signal) => signal.status === "active").length;
  const averageConfidence =
    signals.length > 0
      ? signals.reduce((sum, signal) => sum + signal.confidence, 0) / signals.length
      : 0;
  // Win rate / R come from the closed track record, not the live queue — so they
  // are real telemetry and `—` until trades have actually resolved.
  const overall = performance?.overall;
  const hasTrackRecord = (overall?.total ?? 0) > 0;
  const winRateLabel = hasTrackRecord ? formatPercent(overall!.winRate) : DASH;
  const cadenceMinutes = pipelineQuery.data?.interval_minutes ?? null;
  const cadenceLabel = cadenceMinutes !== null ? `${cadenceMinutes}m` : DASH;

  const engineItems: Array<{ label: string; value: string; tone: "success" | "info" | "neutral" }> = [
    { label: "Monitored pairs", value: `${monitoredPairs} active`, tone: "success" },
    {
      label: "Provider",
      value: latestRun?.ai_provider ?? pipelineQuery.data?.last_run?.ai_provider ?? "—",
      tone: "info"
    },
    {
      label: "Scheduler",
      value: cadenceMinutes !== null ? `${cadenceMinutes} min cadence` : "—",
      tone: "neutral"
    }
  ];

  function refreshMarketData() {
    void pairsQuery.refetch();
    void signalsQuery.refetch();
    void analysisRunsQuery.refetch();
    void performanceQuery.refetch();
    void pipelineQuery.refetch();
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
                  <HeroPill label="Conviction" value={formatPercent(averageConfidence)} />
                  <HeroPill label="Model edge" value={winRateLabel} />
                  <HeroPill label="Live setups" value={activeSignals.toString()} />
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
              <Metric label="Active signals" value={activeSignals.toString()} />
              <Metric label="Average confidence" value={formatPercent(averageConfidence)} />
              <div className="border-t border-[var(--panel-border)] pt-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-[var(--muted)]">Track record</span>
                  <span className="text-xs font-medium text-[var(--muted)]">
                    {hasTrackRecord ? `${overall!.total} closed` : "no closed trades yet"}
                  </span>
                </div>
                <div className="mt-4 space-y-3">
                  <Metric label="Win rate" value={winRateLabel} />
                  <Metric label="Profit factor" value={formatProfitFactor(overall?.profitFactor)} />
                  <Metric
                    label="Net R"
                    value={hasTrackRecord ? (formatR(overall!.totalR) ?? DASH) : DASH}
                  />
                </div>
              </div>
              <div className="rounded-lg border border-[#244d7d] bg-[var(--blue-soft)] p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-[var(--blue-strong)]">
                  <Clock3 className="h-4 w-4" />
                  Next decision window
                </div>
                <p className="mt-2 text-sm leading-6 text-[#b9c7d9]">
                  {cadenceMinutes !== null
                    ? `The pipeline re-scans every ${cadenceMinutes} minutes; setups refresh automatically.`
                    : "Setups refresh automatically as each scheduled scan completes."}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Monitored pairs" value={monitoredPairs.toString()} />
          <StatCard label="Analysis cadence" value={cadenceLabel} />
          <StatCard label="Win rate" value={winRateLabel} />
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
                {engineItems.map((item) => (
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
        </div>
      </section>
    </div>
  );
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

function HeroPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[#2d3647] bg-[#111722] px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-[#7f8da3]">{label}</p>
      <p className="mt-1 text-xl font-semibold text-[var(--gold-strong)]">{value}</p>
    </div>
  );
}
