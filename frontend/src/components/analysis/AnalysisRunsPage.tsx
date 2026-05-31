"use client";

import { CalendarClock, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useAnalysisRunsQuery } from "@/hooks/useTradeQueries";
import { formatDateTime } from "@/lib/formatters";
import type { ApiAnalysisRunStatus } from "@/types/tradeApi";

const statusTone = {
  pending: "neutral",
  running: "info",
  success: "success",
  partial: "neutral",
  failed: "danger"
} satisfies Record<ApiAnalysisRunStatus, "neutral" | "info" | "success" | "danger">;

export function AnalysisRunsPage() {
  const runsQuery = useAnalysisRunsQuery();
  const runs = runsQuery.data?.data ?? [];

  function refresh() {
    void runsQuery.refetch();
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-[#fff8df]">Analysis Runs</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Track scheduler and manual pipeline runs, provider metadata, and pair-level outcomes.
          </p>
        </div>
        <Button disabled={runsQuery.isFetching} onClick={refresh} variant="primary">
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {runsQuery.error ? (
        <ErrorState error={runsQuery.error} onRetry={refresh} title="Analysis ledger unavailable" />
      ) : null}

      {runsQuery.isLoading ? (
        <Card>
          <CardContent>
            <LoadingSpinner label="Loading analysis runs" />
          </CardContent>
        </Card>
      ) : runs.length > 0 ? (
        <div className="grid gap-4">
          {runs.map((run) => (
            <Card key={run.id}>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <CalendarClock className="h-4 w-4 text-[var(--gold)]" />
                      <h2 className="text-lg font-semibold text-[#fff8df]">
                        {formatDateTime(run.started_at)}
                      </h2>
                      <Badge tone={statusTone[run.status]}>{run.status}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-[var(--muted)]">
                      {run.trigger} run on {run.timeframe} using {run.candle_count} candles
                    </p>
                  </div>
                  <p className="text-sm font-semibold text-[#fff8df]">
                    {run.pairs_processed} processed / {run.pairs_failed} failed
                  </p>
                </div>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-3">
                <RunMetric label="Finished" value={run.finished_at ? formatDateTime(run.finished_at) : "Pending"} />
                <RunMetric label="Provider" value={run.ai_provider ?? "Unknown"} />
                <RunMetric label="Model" value={run.ai_model ?? "Unknown"} />
                {run.error_message ? (
                  <div className="rounded-lg border border-[#6e2029] bg-[var(--red-soft)] p-4 text-sm leading-6 text-[#ffc4c7] sm:col-span-3">
                    {run.error_message}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          description="No scheduler or manual analysis runs have been recorded yet."
          title="No analysis runs yet"
        />
      )}
    </section>
  );
}

function RunMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--panel-border)] bg-[#0d131c] p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="mt-2 truncate text-sm font-semibold text-[#fff8df]">{value}</p>
    </div>
  );
}
