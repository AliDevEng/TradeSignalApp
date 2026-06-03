"use client";

import Link from "next/link";
import { ArrowLeft, Bot, Cpu, Layers3, RefreshCw, Timer } from "lucide-react";

import { RelativeTime } from "@/components/common/RelativeTime";
import { SignalCard } from "@/components/signals/SignalCard";
import { SignalListSkeleton } from "@/components/signals/SignalListSkeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useAnalysisRunQuery, useRunSignalsQuery } from "@/hooks/useTradeQueries";
import { formatRunDuration, runStatusTone } from "@/lib/analysisRun";
import { formatDateTime } from "@/lib/formatters";

type AnalysisRunDetailPageProps = {
  runId: string;
};

export function AnalysisRunDetailPage({ runId }: AnalysisRunDetailPageProps) {
  const runQuery = useAnalysisRunQuery(runId);
  const { signalsQuery } = useRunSignalsQuery(runId);

  const run = runQuery.data;
  const signals = signalsQuery.data ?? [];

  function refresh() {
    void runQuery.refetch();
    void signalsQuery.refetch();
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--blue-strong)] transition-colors hover:text-[#8ab8ff]"
            href="/analysis"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to analysis runs
          </Link>
          <h1 className="mt-4 text-3xl font-semibold text-[#fff8df]">Analysis Run</h1>
          <code className="mt-2 block truncate text-xs text-[var(--muted)]">{runId}</code>
        </div>
        <Button
          disabled={runQuery.isFetching || signalsQuery.isFetching}
          onClick={refresh}
          variant="primary"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {runQuery.error ? (
        <ErrorState
          error={runQuery.error as Error}
          onRetry={refresh}
          title="This analysis run could not be loaded"
        />
      ) : null}

      {runQuery.isLoading ? (
        <Card>
          <CardContent>
            <LoadingSpinner label="Loading run" />
          </CardContent>
        </Card>
      ) : run ? (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-semibold text-[#fff8df]">
                  {formatDateTime(run.started_at)}
                </h2>
                <Badge tone={runStatusTone[run.status]}>{run.status}</Badge>
                <Badge tone="neutral">{run.trigger}</Badge>
              </div>
              <p className="text-sm font-semibold text-[#fff8df]">
                {run.pairs_processed} processed / {run.pairs_failed} failed
              </p>
            </div>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <RunMetric icon={Timer} label="Timeframe" value={run.timeframe} />
            <RunMetric icon={Layers3} label="Candles" value={run.candle_count.toString()} />
            <RunMetric
              icon={Timer}
              label="Duration"
              value={formatRunDuration(run.started_at, run.finished_at) ?? "In progress"}
            />
            <RunMetric icon={Bot} label="Provider" value={run.ai_provider ?? "Unknown"} />
            <RunMetric icon={Cpu} label="Model" value={run.ai_model ?? "Unknown"} />
            <RunMetric
              icon={Timer}
              label="Finished"
              value={run.finished_at ? formatDateTime(run.finished_at) : "Pending"}
            />
            {run.error_message ? (
              <div className="rounded-lg border border-[#6e2029] bg-[var(--red-soft)] p-4 text-sm leading-6 text-[#ffc4c7] sm:col-span-2 xl:col-span-3">
                {run.error_message}
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Layers3 className="h-5 w-5 text-[var(--gold)]" />
            <h2 className="text-xl font-semibold text-[#fff8df]">Signals from this run</h2>
            {signalsQuery.isSuccess ? <Badge tone="info">{signals.length}</Badge> : null}
          </div>
          {signalsQuery.isSuccess ? (
            <RelativeTime
              className="text-xs font-medium text-[var(--muted)]"
              prefix="updated"
              value={signalsQuery.dataUpdatedAt}
              intervalMs={5_000}
            />
          ) : null}
        </div>

        {signalsQuery.error ? (
          <ErrorState
            error={signalsQuery.error as Error}
            onRetry={() => void signalsQuery.refetch()}
            title="Could not load this run's signals"
          />
        ) : null}

        {signalsQuery.isLoading ? (
          <SignalListSkeleton />
        ) : signals.length > 0 ? (
          <div className="grid gap-4">
            {signals.map((signal) => (
              <SignalCard density="comfortable" key={signal.id} signal={signal} />
            ))}
          </div>
        ) : (
          <EmptyState
            description="This run did not produce any stored signals — it may have been skipped or every pair returned neutral."
            title="No signals from this run"
          />
        )}
      </section>
    </div>
  );
}

function RunMetric({
  icon: Icon,
  label,
  value
}: {
  icon: typeof Timer;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--panel-border)] bg-[#0d131c] p-4">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        <Icon className="h-4 w-4 text-[var(--gold)]" />
        {label}
      </div>
      <p className="mt-2 truncate text-sm font-semibold text-[#fff8df]">{value}</p>
    </div>
  );
}
