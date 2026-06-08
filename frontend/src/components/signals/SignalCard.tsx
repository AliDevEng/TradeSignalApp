import { memo } from "react";
import Link from "next/link";
import { Brain, Clock3, ShieldCheck, Target } from "lucide-react";

import {
  OutcomeBadge,
  SignalBadge,
  SignalStatusBadge,
  TradeStyleBadge
} from "@/components/signals/SignalBadge";
import { LiveLotSize } from "@/components/risk/LiveLotSize";
import { ConfidenceCalibrationHint } from "@/components/signals/ConfidenceCalibrationHint";
import { Card } from "@/components/ui/Card";
import {
  formatPercent,
  formatPrice,
  formatRiskReward,
  formatTime,
  getPricePrecision
} from "@/lib/formatters";
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
          "grid min-w-0 items-start gap-5 p-4 sm:p-5",
          isCompact
            ? "xl:grid-cols-[minmax(0,1fr)_minmax(280px,360px)]"
            : "xl:grid-cols-[minmax(0,1fr)_minmax(280px,420px)]"
        )}
      >
        <div className="flex min-w-0 flex-col justify-between gap-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="break-words text-2xl font-semibold text-[#fff8df]">
                  {signal.symbol}
                </h3>
                <SignalBadge direction={signal.direction} />
                <TradeStyleBadge tradeStyle={signal.tradeStyle} />
                <SignalStatusBadge status={signal.status} />
                <OutcomeBadge outcome={signal.outcome} realizedR={signal.realizedR} />
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

          {!isCompact ? (
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                Analysis
              </p>
              <p className="mt-2 text-sm leading-7 text-[#c7d1df]">{signal.rationale}</p>
            </div>
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

        <div className="min-w-0 rounded-lg border border-[#263247] bg-[#0b111a] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="rounded-md border border-[#2a3445] bg-[#101722] px-3 py-2.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                Confidence
              </p>
              <p className="mt-1 text-xl font-semibold text-[var(--gold-strong)]">
                {formatPercent(signal.confidence)}
              </p>
            </div>
            <div className="rounded-md border border-[#2a3445] bg-[#101722] px-3 py-2.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                R:R
              </p>
              <p className="mt-1 text-xl font-semibold text-[var(--blue-strong)]">
                {signal.riskReward ? `${formatRiskReward(signal.riskReward)} : 1` : "Hold"}
              </p>
            </div>
          </div>

          <ConfidenceCalibrationHint confidence={signal.confidence} />

          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            <div className="rounded-md border border-[#4a3d20] bg-[#151207] px-3 py-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                <Target className="h-3.5 w-3.5 text-[var(--gold)]" />
                Entry
              </div>
              <p className="mt-2 truncate text-2xl font-semibold leading-none text-[#fff8df]">
                {formatPrice(signal.entryPrice, precision)}
              </p>
            </div>
            <div className="rounded-md border border-[#5a242b] bg-[var(--red-soft)] px-3 py-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                <ShieldCheck className="h-3.5 w-3.5 text-[var(--red-strong)]" />
                Stop
              </div>
              <p className="mt-2 truncate text-2xl font-semibold leading-none text-[#ffdfdf]">
                {signal.stopLoss ? formatPrice(signal.stopLoss, precision) : "Pending"}
              </p>
            </div>
          </div>

          <div className="mt-2 rounded-md border border-[#1f6f49] bg-[#092016] px-3 py-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
              <Brain className="h-3.5 w-3.5 text-[#65d98d]" />
              Targets
            </div>
            {signal.targets.length > 0 ? (
              <ul className="mt-3 grid gap-2">
                {signal.targets.map((target) => (
                  <li
                    key={target.label}
                    className="flex items-center justify-between gap-3 rounded-md bg-[#0d2a1b] px-3 py-2"
                  >
                    <span className="text-xs font-semibold uppercase tracking-wide text-[#b9d8c0]">
                      {target.label}
                    </span>
                    <span className="truncate text-base font-semibold text-[#7bea9b]">
                      {formatPrice(target.price, precision)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-lg font-semibold text-[#7bea9b]">Pending</p>
            )}
          </div>

          <div className="mt-2">
            <LiveLotSize signal={signal} variant="inline" />
          </div>
        </div>
      </div>
    </Card>
  );
});
