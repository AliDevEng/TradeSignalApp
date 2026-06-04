import { EmptyState } from "@/components/ui/EmptyState";
import type { CalibrationBucket } from "@/types/performance";

type CalibrationChartProps = {
  buckets: CalibrationBucket[];
};

/**
 * Confidence calibration: per confidence band, the model's *predicted* hit-rate
 * (mean stated confidence) beside the *realised* hit-rate. A well-calibrated
 * model has the two bars roughly level in every populated band — "when it says
 * 80%, it's right ~80% of the time". Empty bands are kept (greyed) so the x-axis
 * is stable. Pure CSS bars: no chart library, inherently responsive.
 */
export function CalibrationChart({ buckets }: CalibrationChartProps) {
  const populated = buckets.filter((bucket) => bucket.count > 0);

  if (populated.length === 0) {
    return (
      <EmptyState
        description="Calibration compares the AI's stated confidence with how often those calls actually won. It fills in as signals close."
        title="Not enough closed trades yet"
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-3" role="img" aria-label="Confidence calibration by band.">
        {buckets.map((bucket) => {
          const empty = bucket.count === 0;
          return (
            <div className="flex flex-1 flex-col items-center gap-2" key={bucket.label}>
              <div className="flex h-40 w-full items-end justify-center gap-1.5">
                <Bar
                  className="bg-[var(--gold)]"
                  empty={empty}
                  title={`Predicted ${Math.round(bucket.avgConfidence * 100)}%`}
                  value={bucket.avgConfidence}
                />
                <Bar
                  className="bg-[var(--blue)]"
                  empty={empty}
                  title={`Realised ${Math.round(bucket.winRate * 100)}%`}
                  value={bucket.winRate}
                />
              </div>
              <div className="text-center">
                <p className="text-xs font-semibold text-[#cdd5e1]">{bucket.label}</p>
                <p className="text-[10px] font-medium text-[var(--muted)]">
                  {empty ? "—" : `n=${bucket.count}`}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-4 text-xs font-medium text-[var(--muted)]">
        <LegendSwatch className="bg-[var(--gold)]" label="Predicted (stated confidence)" />
        <LegendSwatch className="bg-[var(--blue)]" label="Realised (win rate)" />
      </div>
    </div>
  );
}

function Bar({
  value,
  empty,
  className,
  title
}: {
  value: number;
  empty: boolean;
  className: string;
  title: string;
}) {
  // Floor a visible sliver so a 0% bar still reads as "present but zero".
  const heightPercent = empty ? 2 : Math.max(value * 100, 2);

  return (
    <div
      className={`w-3.5 rounded-t-sm transition-all ${empty ? "bg-[#283143]" : className}`}
      style={{ height: `${heightPercent}%` }}
      title={empty ? "No signals in this band" : title}
    />
  );
}

function LegendSwatch({ className, label }: { className: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`h-2.5 w-2.5 rounded-sm ${className}`} />
      {label}
    </span>
  );
}
