"use client";

import { Activity, Clock3, ServerCog } from "lucide-react";

import { RelativeTime } from "@/components/common/RelativeTime";
import { HealthPanel } from "@/components/health/HealthPanel";
import { PipelineStatusBanner } from "@/components/signals/PipelineStatusBanner";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { useAnalysisRunsQuery, useSignalsQuery } from "@/hooks/useTradeQueries";

function formatRunLabel(
  run: { status: string; trigger: string; timeframe: string } | undefined
): string {
  if (!run) {
    return "Waiting for first run";
  }
  return `${run.status} ${run.trigger} run on ${run.timeframe}`;
}

/**
 * System & status page (Iteration 13 redesign): backend health, the live analysis
 * pipeline, and scan cadence — the infrastructure telemetry that used to crowd the
 * trader's dashboard, now on its own surface where it belongs.
 */
export function SystemPage() {
  const { signalsQuery } = useSignalsQuery();
  const analysisRunsQuery = useAnalysisRunsQuery();
  const latestRun = analysisRunsQuery.data?.data[0];
  const openSignals = (signalsQuery.data?.signals ?? []).filter(
    (signal) => signal.outcome === "open"
  ).length;

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="flex items-center gap-2 text-xl font-semibold text-[#fff8df]">
          <ServerCog className="h-5 w-5 text-[var(--gold)]" />
          System &amp; status
        </h1>
        <p className="text-sm text-[var(--muted)]">
          Backend health, the live analysis pipeline, and data-provider status. Everything the desk
          relies on, in one place.
        </p>
      </header>

      <PipelineStatusBanner />

      <section className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Clock3 className="h-4 w-4 text-[var(--blue-strong)]" />
              <h2 className="font-semibold">Pipeline</h2>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <Row label="Signals open" value={openSignals.toString()} />
            <Row label="Latest run" value={formatRunLabel(latestRun)} />
            {signalsQuery.isSuccess ? (
              <RelativeTime
                className="block text-xs font-medium text-[var(--muted)]"
                intervalMs={5_000}
                prefix="Auto-refreshing — updated"
                value={signalsQuery.dataUpdatedAt}
              />
            ) : null}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-[var(--blue-strong)]" />
              <h2 className="font-semibold">Backend health</h2>
            </div>
          </CardHeader>
          <CardContent>
            <HealthPanel />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm text-[var(--muted)]">{label}</span>
      <span className="max-w-[60%] text-right text-sm font-semibold capitalize text-[#fff8df]">
        {value}
      </span>
    </div>
  );
}
