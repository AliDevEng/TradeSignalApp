import { Activity } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDateTime, formatIndicator } from "@/lib/formatters";
import { buildIndicatorGroups, type IndicatorTone } from "@/lib/indicators";
import { cn } from "@/lib/utils";
import type { IndicatorSnapshot } from "@/types/signal";

type IndicatorsPanelProps = {
  indicators: IndicatorSnapshot | null;
};

const toneClasses: Record<IndicatorTone, string> = {
  neutral: "text-[#fff8df]",
  bullish: "text-[var(--gold-strong)]",
  bearish: "text-[var(--red-strong)]"
};

const hintClasses: Record<IndicatorTone, string> = {
  neutral: "text-[var(--muted)]",
  bullish: "text-[var(--gold)]",
  bearish: "text-[var(--red-strong)]"
};

export function IndicatorsPanel({ indicators }: IndicatorsPanelProps) {
  return (
    <Card>
      <CardHeader className="space-y-2">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-[var(--gold)]" />
          <h2 className="text-lg font-semibold text-[#fff8df]">Indicator Snapshot</h2>
        </div>
        {indicators?.asOf ? (
          <p className="text-sm text-[var(--muted)]">
            Captured {formatDateTime(indicators.asOf)} from {indicators.candlesAnalyzed} candles
            {indicators.lastClose !== null
              ? ` · last close ${formatIndicator(indicators.lastClose)}`
              : ""}
          </p>
        ) : (
          <p className="text-sm text-[var(--muted)]">
            The exact indicator values that fed the model at generation time.
          </p>
        )}
      </CardHeader>
      <CardContent>
        {indicators === null ? (
          <EmptyState
            description="This signal was stored without an indicator snapshot, so there is nothing to break down here."
            title="No indicator data"
          />
        ) : (
          <div className="grid gap-5 md:grid-cols-3">
            {buildIndicatorGroups(indicators).map((group) => (
              <div key={group.title}>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                  {group.title}
                </h3>
                <dl className="mt-3 space-y-2">
                  {group.rows.map((row) => (
                    <div
                      className="flex items-baseline justify-between gap-3 rounded-md border border-[var(--panel-border)] bg-[#0d131c] px-3 py-2"
                      key={row.label}
                    >
                      <dt className="text-sm text-[var(--muted)]">{row.label}</dt>
                      <dd className="text-right">
                        <span className={cn("text-sm font-semibold", toneClasses[row.tone])}>
                          {row.value}
                        </span>
                        {row.hint ? (
                          <span
                            className={cn(
                              "ml-2 text-xs font-medium uppercase tracking-wide",
                              hintClasses[row.tone]
                            )}
                          >
                            {row.hint}
                          </span>
                        ) : null}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
