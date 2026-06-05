"use client";

import { useMemo, useSyncExternalStore } from "react";
import { RefreshCw } from "lucide-react";

import { CalibrationChart } from "@/components/charts/CalibrationChart";
import { EquityCurveChart } from "@/components/charts/EquityCurveChart";
import { RelativeTime } from "@/components/common/RelativeTime";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { usePerformanceQuery } from "@/hooks/useTradeQueries";
import { PREVIEW_DATA_ENABLED } from "@/lib/env";
import { buildPerformanceFromSignals } from "@/lib/performance";
import { signals as mockSignals } from "@/lib/mockSignals";
import { formatR } from "@/lib/outcome";
import type { Performance, PerformanceSummary } from "@/types/performance";
import type { SignalTradeStyle } from "@/types/signal";

const subscribeToHydration = () => () => undefined;

function formatWinRate(summary: PerformanceSummary): string {
  return summary.total > 0 ? `${Math.round(summary.winRate * 100)}%` : "—";
}

function formatProfitFactor(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return value.toFixed(2);
}

function formatRValue(value: number, total: number): string {
  return total > 0 ? (formatR(value) ?? "0.00R") : "—";
}

const STYLE_LABELS: Record<SignalTradeStyle, string> = {
  scalp: "Scalp",
  swing: "Swing"
};

export function PerformanceDashboardPage() {
  const query = usePerformanceQuery();
  const hasMounted = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false
  );

  const isQueryError = hasMounted && query.isError;
  // Preview mode only: derive a track record from bundled sample signals so the
  // page demonstrates its shape offline. Off by default — otherwise we'd show a
  // fabricated track record as if it were the real one.
  const showPreview = isQueryError && PREVIEW_DATA_ENABLED;

  const fallback = useMemo(() => buildPerformanceFromSignals(mockSignals), []);
  const performance: Performance | null = showPreview
    ? fallback
    : hasMounted
      ? (query.data ?? null)
      : null;

  const isInitialLoading = !hasMounted || (query.isLoading && !query.isError);

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-[#fff8df]">Performance</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            The scoreboard: win-rate, profit factor, and expectancy over every closed signal, an
            equity curve of cumulative R, and a confidence-calibration read on whether the AI&apos;s
            stated odds actually hold up.
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

      {isQueryError ? (
        <ErrorState
          error={query.error as Error}
          onRetry={() => void query.refetch()}
          title={showPreview ? "Live API unavailable, showing preview data" : "Live API unavailable"}
        />
      ) : null}

      {hasMounted && !isQueryError && query.isSuccess ? (
        <p className="text-xs font-medium text-[var(--muted)]">
          <RelativeTime prefix="updated" value={query.dataUpdatedAt} intervalMs={5_000} />
        </p>
      ) : null}

      {isInitialLoading ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner />
        </div>
      ) : performance === null ? (
        // Errored with preview off (ErrorState shown above) or genuinely no data.
        isQueryError ? null : (
          <EmptyState
            description="Once signals close with a realised R, the track record charts here."
            title="No performance data yet"
          />
        )
      ) : (
        <div className="space-y-5">
          <OverallKpis summary={performance.overall} />

          <div className="grid gap-4 lg:grid-cols-2">
            <StyleSummaryCard label={STYLE_LABELS.scalp} summary={performance.byType.scalp} />
            <StyleSummaryCard label={STYLE_LABELS.swing} summary={performance.byType.swing} />
          </div>

          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-[#fff8df]">Equity curve</h2>
              <p className="mt-1 text-sm text-[var(--muted)]">
                Cumulative realised R as each signal resolves.
              </p>
            </CardHeader>
            <CardContent>
              <EquityCurveChart points={performance.equityCurve} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-[#fff8df]">Confidence calibration</h2>
              <p className="mt-1 text-sm text-[var(--muted)]">
                Predicted vs realised hit-rate by confidence band — is the AI honest about its odds?
              </p>
            </CardHeader>
            <CardContent>
              <CalibrationChart buckets={performance.calibration} />
            </CardContent>
          </Card>
        </div>
      )}
    </section>
  );
}

function OverallKpis({ summary }: { summary: PerformanceSummary }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        hint={`${summary.wins} W / ${summary.losses} L · ${summary.total} closed`}
        label="Win rate"
        tone="win"
        value={formatWinRate(summary)}
      />
      <KpiCard
        hint="Gross profit ÷ gross loss"
        label="Profit factor"
        tone={summary.profitFactor !== null && summary.profitFactor >= 1 ? "win" : "default"}
        value={formatProfitFactor(summary.profitFactor)}
      />
      <KpiCard
        hint="Average R per signal"
        label="Expectancy"
        tone={summary.avgR >= 0 ? "win" : "loss"}
        value={formatRValue(summary.avgR, summary.total)}
      />
      <KpiCard
        hint="Net realised R"
        label="Total R"
        tone={summary.totalR >= 0 ? "win" : "loss"}
        value={formatRValue(summary.totalR, summary.total)}
      />
    </div>
  );
}

function StyleSummaryCard({ label, summary }: { label: string; summary: PerformanceSummary }) {
  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-[#fff8df]">{label}</h3>
        <span className="text-xs font-medium text-[var(--muted)]">{summary.total} closed</span>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MiniStat label="Win rate" tone="win" value={formatWinRate(summary)} />
        <MiniStat label="Profit factor" value={formatProfitFactor(summary.profitFactor)} />
        <MiniStat
          label="Expectancy"
          tone={summary.avgR >= 0 ? "win" : "loss"}
          value={formatRValue(summary.avgR, summary.total)}
        />
        <MiniStat
          label="Total R"
          tone={summary.totalR >= 0 ? "win" : "loss"}
          value={formatRValue(summary.totalR, summary.total)}
        />
      </CardContent>
    </Card>
  );
}

type Tone = "default" | "win" | "loss";

function toneClass(tone: Tone): string {
  if (tone === "win") {
    return "text-[#7bea9b]";
  }
  if (tone === "loss") {
    return "text-[var(--red-strong)]";
  }
  return "text-[#fff8df]";
}

function KpiCard({
  label,
  value,
  hint,
  tone = "default"
}: {
  label: string;
  value: string;
  hint: string;
  tone?: Tone;
}) {
  return (
    <div className="rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] px-4 py-3 shadow-[var(--surface-shadow)]">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className={`mt-1 text-3xl font-semibold ${toneClass(tone)}`}>{value}</p>
      <p className="mt-1 text-xs font-medium text-[var(--muted)]">{hint}</p>
    </div>
  );
}

function MiniStat({ label, value, tone = "default" }: { label: string; value: string; tone?: Tone }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
        {label}
      </p>
      <p className={`mt-1 text-lg font-semibold ${toneClass(tone)}`}>{value}</p>
    </div>
  );
}
