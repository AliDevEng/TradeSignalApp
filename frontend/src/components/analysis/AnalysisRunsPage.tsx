"use client";

import { useState } from "react";
import Link from "next/link";
import { CalendarClock, PlayCircle, RefreshCw } from "lucide-react";

import { RelativeTime } from "@/components/common/RelativeTime";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Pagination } from "@/components/ui/Pagination";
import { useAnalysisRunsQuery, useTriggerAnalysisRun } from "@/hooks/useTradeQueries";
import { track } from "@/lib/analytics";
import { formatDateTime } from "@/lib/formatters";
import { runStatusOptions, runStatusTone } from "@/lib/analysisRun";
import { cn } from "@/lib/utils";
import { toast } from "@/store/toastStore";
import type { ApiAnalysisRunStatus } from "@/types/tradeApi";

type StatusFilter = "all" | ApiAnalysisRunStatus;

export function AnalysisRunsPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const runsQuery = useAnalysisRunsQuery({
    page,
    status: statusFilter === "all" ? undefined : statusFilter
  });
  const trigger = useTriggerAnalysisRun();

  const runs = runsQuery.data?.data ?? [];
  const pagination = runsQuery.data?.pagination;

  function changeStatus(next: StatusFilter) {
    setStatusFilter(next);
    setPage(1);
  }

  function triggerRun() {
    trigger.mutate(undefined, {
      onSuccess: () => {
        track({ name: "analysis_run_triggered", source: "analysis-page" });
        toast({
          tone: "success",
          title: "Analysis run scheduled",
          description: "Watching the ledger — the new run will appear here as it completes."
        });
        setPage(1);
        setStatusFilter("all");
      },
      onError: (error) => {
        toast({
          tone: "danger",
          title: "Could not trigger run",
          description: error instanceof Error ? error.message : "Unexpected error."
        });
      }
    });
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-[#fff8df]">Analysis Runs</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Track scheduler and manual pipeline runs, provider metadata, and pair-level outcomes.
          </p>
          {runsQuery.isSuccess ? (
            <p className="mt-2 text-xs font-medium text-[var(--muted)]">
              <RelativeTime prefix="updated" value={runsQuery.dataUpdatedAt} intervalMs={5_000} />
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <Button disabled={trigger.isPending} onClick={triggerRun} variant="primary">
            <PlayCircle className="h-4 w-4" />
            {trigger.isPending ? "Triggering…" : "Trigger analysis run"}
          </Button>
          <Button
            aria-label="Refresh runs"
            disabled={runsQuery.isFetching}
            onClick={() => void runsQuery.refetch()}
            size="icon"
            variant="secondary"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <StatusChip active={statusFilter === "all"} label="All" onClick={() => changeStatus("all")} />
        {runStatusOptions.map((status) => (
          <StatusChip
            active={statusFilter === status}
            key={status}
            label={status}
            onClick={() => changeStatus(status)}
          />
        ))}
      </div>

      {runsQuery.error ? (
        <ErrorState
          error={runsQuery.error as Error}
          onRetry={() => void runsQuery.refetch()}
          title="Analysis ledger unavailable"
        />
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
            <Link
              className="block rounded-lg transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--gold)]"
              href={`/analysis/${run.id}`}
              key={run.id}
            >
              <Card className="transition-colors hover:border-[#6f5620]">
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <CalendarClock className="h-4 w-4 text-[var(--gold)]" />
                        <h2 className="text-lg font-semibold text-[#fff8df]">
                          {formatDateTime(run.started_at)}
                        </h2>
                        <Badge tone={runStatusTone[run.status]}>{run.status}</Badge>
                        <Badge tone="neutral">{run.trigger}</Badge>
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
                  <RunMetric
                    label="Finished"
                    value={run.finished_at ? formatDateTime(run.finished_at) : "Pending"}
                  />
                  <RunMetric label="Provider" value={run.ai_provider ?? "Unknown"} />
                  <RunMetric label="Model" value={run.ai_model ?? "Unknown"} />
                  {run.error_message ? (
                    <div className="rounded-lg border border-[#6e2029] bg-[var(--red-soft)] p-4 text-sm leading-6 text-[#ffc4c7] sm:col-span-3">
                      {run.error_message}
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState
          description="No scheduler or manual analysis runs match this filter yet."
          title="No analysis runs"
        />
      )}

      {pagination ? (
        <Pagination
          disabled={runsQuery.isFetching}
          onPageChange={setPage}
          page={pagination.page}
          totalPages={pagination.pages}
        />
      ) : null}
    </section>
  );
}

function StatusChip({
  active,
  label,
  onClick
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-pressed={active}
      className={cn(
        "rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-wide capitalize transition-colors",
        active
          ? "border-[#6f5620] bg-[var(--gold)] text-[#0a0c10]"
          : "border-[var(--panel-border)] bg-[#111722] text-[var(--muted)] hover:text-[#fff8df]"
      )}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
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
