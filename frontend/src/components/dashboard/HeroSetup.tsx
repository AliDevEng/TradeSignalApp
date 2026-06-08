"use client";

import Link from "next/link";
import { ArrowUpRight, Clock3, ShieldCheck, Target, Zap } from "lucide-react";

import { LiveLotSize } from "@/components/risk/LiveLotSize";
import { SignalStatusBadge, TradeStyleBadge } from "@/components/signals/SignalBadge";
import { ConfidenceGauge } from "@/components/ui/ConfidenceGauge";
import { RiskRewardBar } from "@/components/ui/RiskRewardBar";
import { formatPrice, formatSignedPercent, formatTime, getPricePrecision } from "@/lib/formatters";
import type { Signal } from "@/types/signal";

/**
 * The dashboard's hero: the single highest-conviction live setup rendered big and
 * decision-first — confidence dial, reward:risk, the exact trade levels, and a
 * live lot size sized to the user's account, all above the fold. This is what a
 * trader opens the app to see.
 */
export function HeroSetup({ signal }: { signal: Signal }) {
  const precision = getPricePrecision(signal.symbol);
  const directionTone =
    signal.direction === "buy"
      ? "text-[#65d98d]"
      : signal.direction === "sell"
        ? "text-[var(--red-strong)]"
        : "text-[var(--muted)]";

  return (
    <section className="relative overflow-hidden rounded-xl border border-[#3a2f14] bg-gradient-to-br from-[#15110a] via-[#0d131c] to-[#0b0f17] p-5 shadow-[var(--surface-shadow)] sm:p-6">
      <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-[var(--gold)] opacity-[0.06] blur-3xl" />

      <div className="relative flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 rounded-full border border-[#6f5620] bg-[#191407] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[var(--gold-strong)]">
          <Zap className="h-3.5 w-3.5" />
          Top setup right now
        </span>
        <Link
          className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--blue-strong)] transition-colors hover:text-[#8ab8ff]"
          href={`/signals/${signal.id}`}
        >
          Open signal
          <ArrowUpRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="relative mt-5 grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        {/* Left: identity, thesis, R:R, levels */}
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <h2 className="text-4xl font-bold tracking-tight text-[#fff8df]">{signal.symbol}</h2>
            <span className={`text-xl font-bold uppercase ${directionTone}`}>
              {signal.direction}
            </span>
            <TradeStyleBadge tradeStyle={signal.tradeStyle} />
            <SignalStatusBadge status={signal.status} />
          </div>
          <p className="mt-1 text-sm text-[var(--muted)]">{signal.displayName}</p>

          <p className="mt-4 line-clamp-3 text-sm leading-6 text-[#c7d1df]">{signal.rationale}</p>

          <div className="mt-5 max-w-md">
            <RiskRewardBar ratio={signal.riskReward} />
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            <LevelTile
              icon={Target}
              label="Entry"
              tone="gold"
              value={formatPrice(signal.entryPrice, precision)}
            />
            <LevelTile
              icon={ShieldCheck}
              label="Stop"
              sub={
                signal.stopDistancePercent !== null
                  ? formatSignedPercent(signal.stopDistancePercent)
                  : undefined
              }
              tone="red"
              value={signal.stopLoss ? formatPrice(signal.stopLoss, precision) : "—"}
            />
            {signal.targets.slice(0, 2).map((target) => (
              <LevelTile
                icon={Target}
                key={target.label}
                label={target.label}
                sub={
                  target.distancePercent !== null
                    ? formatSignedPercent(target.distancePercent)
                    : undefined
                }
                tone="green"
                value={formatPrice(target.price, precision)}
              />
            ))}
          </div>

          <p className="mt-4 inline-flex items-center gap-1.5 text-xs font-medium text-[var(--muted)]">
            <Clock3 className="h-3.5 w-3.5" />
            Generated {formatTime(signal.generatedAt)}
            {signal.expiresAt ? ` · expires ${formatTime(signal.expiresAt)}` : ""}
          </p>
        </div>

        {/* Right: confidence dial + live sizing + CTA */}
        <div className="flex flex-col items-center gap-4 rounded-xl border border-[#263247] bg-[#0b111a]/70 p-5">
          <ConfidenceGauge value={signal.confidence} />
          <LiveLotSize className="w-full" signal={signal} variant="panel" />
          <Link
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-[#8f6a20] bg-[var(--gold)] px-4 py-2.5 text-sm font-semibold text-[#0a0c10] transition-colors hover:bg-[var(--gold-strong)]"
            href={`/signals/${signal.id}`}
          >
            Review full setup
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}

function LevelTile({
  icon: Icon,
  label,
  value,
  sub,
  tone
}: {
  icon: typeof Target;
  label: string;
  value: string;
  sub?: string;
  tone: "gold" | "red" | "green";
}) {
  const styles = {
    gold: { border: "border-[#4a3d20]", bg: "bg-[#151207]", icon: "text-[var(--gold)]", value: "text-[#fff8df]" },
    red: { border: "border-[#5a242b]", bg: "bg-[var(--red-soft)]", icon: "text-[var(--red-strong)]", value: "text-[#ffdfdf]" },
    green: { border: "border-[#1f6f49]", bg: "bg-[#092016]", icon: "text-[#65d98d]", value: "text-[#bfe6c8]" }
  }[tone];

  return (
    <div className={`min-w-0 rounded-lg border ${styles.border} ${styles.bg} px-3 py-2.5`}>
      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
        <Icon className={`h-3 w-3 ${styles.icon}`} />
        {label}
      </div>
      <p className={`mt-1.5 truncate text-lg font-bold leading-none ${styles.value}`}>{value}</p>
      {sub ? <p className="mt-1 text-[11px] font-medium text-[var(--muted)]">{sub}</p> : null}
    </div>
  );
}
