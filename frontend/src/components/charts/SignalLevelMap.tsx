import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { SignalOverlay } from "@/components/charts/SignalOverlay";
import { OutcomeBadge } from "@/components/signals/SignalBadge";
import { formatPrice, formatSignedPercent, getPricePrecision } from "@/lib/formatters";
import { formatR, isClosedOutcome } from "@/lib/outcome";
import {
  getIndicatorReferenceLevels,
  getSignalPriceLevels,
  type SignalPriceLevelTone
} from "@/lib/trading";
import type { Signal, SignalOutcome } from "@/types/signal";

type SignalLevelMapProps = {
  signal: Signal;
  title: string;
  subtitle: string;
};

const toneStyles: Record<SignalPriceLevelTone, { line: string; dot: string; text: string }> = {
  entry: { line: "bg-[var(--gold)]", dot: "bg-[var(--gold)]", text: "text-[var(--gold-strong)]" },
  stop: { line: "bg-[var(--red)]", dot: "bg-[var(--red)]", text: "text-[var(--red-strong)]" },
  target: { line: "bg-[var(--blue)]", dot: "bg-[var(--blue)]", text: "text-[var(--blue-strong)]" }
};

/**
 * The id of the price level price actually reached, derived from the outcome —
 * so the map can mark *where the trade resolved* without a live price feed.
 */
function reachedLevelId(signal: Signal): string | null {
  const byOutcome: Partial<Record<SignalOutcome, string>> = {
    hit_tp1: `${signal.id}-tp1`,
    hit_tp2: `${signal.id}-tp2`,
    hit_tp3: `${signal.id}-tp3`,
    hit_sl: `${signal.id}-stop`
  };
  return byOutcome[signal.outcome] ?? null;
}

/** Vertical position (0 = top) for a price within a padded [min,max] domain. */
function positionPercent(price: number, min: number, max: number): number {
  if (max === min) {
    return 50;
  }

  return ((max - price) / (max - min)) * 100;
}

/**
 * A price-axis "level map": entry, stop, and the take-profit ladder plotted
 * against indicator-derived reference levels (EMAs, Bollinger bands). This is
 * the chart per the Iteration 6 decision — driven by signal data + indicators
 * rather than an OHLCV history feed.
 */
export function SignalLevelMap({ signal, title, subtitle }: SignalLevelMapProps) {
  const precision = getPricePrecision(signal.symbol);
  const levels = getSignalPriceLevels(signal);
  const references = getIndicatorReferenceLevels(signal.id, signal.indicators);

  const prices = [...levels.map((level) => level.price), ...references.map((ref) => ref.price)];
  const rawMin = Math.min(...prices);
  const rawMax = Math.max(...prices);
  const padding = (rawMax - rawMin || rawMax || 1) * 0.08;
  const min = rawMin - padding;
  const max = rawMax + padding;

  const chartLabel = `Price level map for ${signal.symbol}: ${levels
    .map((level) => `${level.label} ${formatPrice(level.price, precision)}`)
    .join(", ")}.`;

  const reachedId = reachedLevelId(signal);
  const isClosed = isClosedOutcome(signal.outcome);
  const realized = formatR(signal.realizedR);

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-[#fff8df]">{title}</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">{subtitle}</p>
          </div>
          {isClosed ? (
            <div className="flex items-center gap-2">
              <OutcomeBadge outcome={signal.outcome} realizedR={signal.realizedR} />
              {realized ? (
                <span className="text-sm font-semibold text-[var(--muted)]">
                  Realized{" "}
                  <span
                    className={
                      (signal.realizedR ?? 0) >= 0 ? "text-[#7bea9b]" : "text-[var(--red-strong)]"
                    }
                  >
                    {realized}
                  </span>
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
        <SignalOverlay signal={signal} />
      </CardHeader>
      <CardContent>
        <div
          aria-label={chartLabel}
          className="relative h-[420px] w-full overflow-hidden rounded-lg border border-[var(--panel-border)] bg-[#0d131c]"
          role="img"
        >
          {/* Indicator reference levels: subtle context behind the trade plan. */}
          {references.map((reference) => {
            const top = positionPercent(reference.price, min, max);
            return (
              <div
                className="absolute left-0 right-0 flex items-center"
                key={reference.id}
                style={{ top: `${top}%` }}
              >
                <div className="h-px w-full border-t border-dashed border-[#3a4761]" />
                <span className="absolute left-3 -translate-y-1/2 rounded bg-[#101722] px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[#7f8da3]">
                  {reference.label} {formatPrice(reference.price, precision)}
                </span>
              </div>
            );
          })}

          {/* Trade-plan levels: entry, stop, and target ladder. */}
          {levels.map((level) => {
            const top = positionPercent(level.price, min, max);
            const styles = toneStyles[level.tone];
            const isReached = level.id === reachedId;
            const reachedRing = level.tone === "stop" ? "ring-[var(--red)]" : "ring-[#2c8155]";
            return (
              <div
                className="absolute left-0 right-0 flex items-center"
                key={level.id}
                style={{ top: `${top}%` }}
              >
                <div
                  className={`h-0.5 w-full ${styles.line} ${isReached ? "opacity-100" : "opacity-80"}`}
                />
                <div
                  className={`absolute right-3 -translate-y-1/2 flex items-center gap-2 rounded-md border border-[var(--panel-border)] bg-[#0b0f17] px-3 py-1.5 ${
                    isReached ? `ring-2 ${reachedRing}` : ""
                  }`}
                >
                  <span className={`h-2 w-2 rounded-full ${styles.dot}`} />
                  <span className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                    {level.label}
                  </span>
                  <span className={`text-sm font-semibold ${styles.text}`}>
                    {formatPrice(level.price, precision)}
                  </span>
                  {level.distancePercent !== null ? (
                    <span className="text-xs font-medium text-[var(--muted)]">
                      {formatSignedPercent(level.distancePercent)}
                    </span>
                  ) : null}
                  {isReached ? (
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wide ${
                        level.tone === "stop" ? "text-[var(--red-strong)]" : "text-[#7bea9b]"
                      }`}
                    >
                      {level.tone === "stop" ? "✗ hit" : "✓ reached"}
                    </span>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
