import { memo } from "react";
import Link from "next/link";
import { Brain, Clock3, ShieldCheck, Target } from "lucide-react";

import { SignalBadge, SignalStatusBadge, TradeStyleBadge } from "@/components/signals/SignalBadge";
import { Card } from "@/components/ui/Card";
import { formatPercent, formatPrice, formatTime, getPricePrecision } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import type { Signal } from "@/types/signal";

type SignalCardProps = {
  signal: Signal;
  density: "comfortable" | "compact";
};

// Memoised: cards render in long lists and their props (signal + density) are
// referentially stable across parent re-renders driven by polling/filters.
export const SignalCard = memo(function SignalCard({ signal, density }: SignalCardProps) {
  const precision = getPricePrecision(signal.symbol);
  const isCompact = density === "compact";

  return (
    <Card className="overflow-hidden transition-colors hover:border-[#6f5620]">
      <div
        className={cn(
          "grid gap-5 p-5",
          isCompact ? "lg:grid-cols-[1fr_1.2fr]" : "lg:grid-cols-[1fr_1.4fr]"
        )}
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-xl font-semibold text-[#fff8df]">{signal.symbol}</h3>
                <SignalBadge direction={signal.direction} />
                <TradeStyleBadge tradeStyle={signal.tradeStyle} />
                <SignalStatusBadge status={signal.status} />
              </div>
              <p className="mt-1 text-sm text-[var(--muted)]">{signal.displayName}</p>
            </div>
            <Link
              className="text-sm font-semibold text-[var(--blue-strong)] transition-colors hover:text-[#8ab8ff]"
              href={`/pairs/${signal.symbol}`}
            >
              Pair view
            </Link>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-md border border-[#2a3445] bg-[#0e141e] px-3 py-2">
              <p className="text-xs font-medium text-[var(--muted)]">Confidence</p>
              <p className="mt-1 text-lg font-semibold text-[var(--gold-strong)]">
                {formatPercent(signal.confidence)}
              </p>
            </div>
            <div className="rounded-md border border-[#2a3445] bg-[#0e141e] px-3 py-2">
              <p className="text-xs font-medium text-[var(--muted)]">R:R</p>
              <p className="mt-1 text-lg font-semibold text-[var(--blue-strong)]">
                {signal.riskReward ? `${signal.riskReward.toFixed(2)} : 1` : "Hold"}
              </p>
            </div>
          </div>
        </div>

        <div className="grid gap-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-md border border-[#334056] bg-[#0d131c] p-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                <Target className="h-3.5 w-3.5 text-[var(--gold)]" />
                Entry
              </div>
              <p className="mt-2 text-lg font-semibold text-[#fff8df]">
                {formatPrice(signal.entryPrice, precision)}
              </p>
            </div>
            <div className="rounded-md border border-[#4c2027] bg-[var(--red-soft)] p-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                <ShieldCheck className="h-3.5 w-3.5 text-[var(--red-strong)]" />
                Stop
              </div>
              <p className="mt-2 text-lg font-semibold text-[#fff8df]">
                {signal.stopLoss ? formatPrice(signal.stopLoss, precision) : "Pending"}
              </p>
            </div>
            <div className="rounded-md border border-[#244d7d] bg-[var(--blue-soft)] p-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                <Brain className="h-3.5 w-3.5 text-[var(--blue-strong)]" />
                Targets
              </div>
              {signal.targets.length > 0 ? (
                <ul className="mt-2 space-y-1">
                  {signal.targets.map((target) => (
                    <li key={target.label} className="flex items-baseline justify-between gap-2">
                      <span className="text-xs font-medium text-[var(--muted)]">{target.label}</span>
                      <span className="text-sm font-semibold text-[#fff8df]">
                        {formatPrice(target.price, precision)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-lg font-semibold text-[#fff8df]">Pending</p>
              )}
            </div>
          </div>

          {!isCompact ? (
            <p className="text-sm leading-6 text-[#b8c2d0]">{signal.rationale}</p>
          ) : null}

          <div className="flex flex-wrap items-center gap-3 text-xs font-medium text-[var(--muted)]">
            <span className="inline-flex items-center gap-1.5">
              <Clock3 className="h-3.5 w-3.5" />
              Generated {formatTime(signal.generatedAt)}
            </span>
            {signal.expiresAt ? <span>Expires {formatTime(signal.expiresAt)}</span> : null}
          </div>

          <div className="flex flex-wrap gap-2">
            <Link
              className="inline-flex min-w-[132px] items-center justify-center rounded-lg border border-[#8f6a20] bg-[var(--gold)] px-4 py-2 text-sm font-semibold text-[#0a0c10] transition-colors hover:bg-[var(--gold-strong)]"
              href={`/signals/${signal.id}`}
            >
              Review signal
            </Link>
          </div>
        </div>
      </div>
    </Card>
  );
});
