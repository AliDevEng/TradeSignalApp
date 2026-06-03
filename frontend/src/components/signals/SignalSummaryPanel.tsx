import { Activity, BarChart3, ShieldCheck, Target, TrendingUp, type LucideIcon } from "lucide-react";

import { SignalBadge, SignalStatusBadge } from "@/components/signals/SignalBadge";
import { Card, CardContent } from "@/components/ui/Card";
import { formatPercent, formatPrice, getPricePrecision } from "@/lib/formatters";
import type { Signal } from "@/types/signal";

type SignalSummaryPanelProps = {
  signal: Signal;
};

export function SignalSummaryPanel({ signal }: SignalSummaryPanelProps) {
  const precision = getPricePrecision(signal.symbol);

  return (
    <Card>
      <CardContent className="grid gap-6 p-5 lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.95fr)] xl:grid-cols-[minmax(0,1.15fr)_minmax(420px,0.85fr)]">
        <div className="flex min-w-0 flex-col justify-between gap-6">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-2xl font-semibold text-[#fff8df]">{signal.symbol}</h2>
              <SignalBadge direction={signal.direction} />
              <SignalStatusBadge status={signal.status} />
            </div>
            <p className="text-sm text-[var(--muted)]">{signal.displayName}</p>
          </div>

          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
              <BarChart3 className="h-4 w-4 text-[var(--gold)]" />
              Analysis
            </div>
            <p className="mt-3 max-w-4xl text-sm leading-7 text-[#c2cad6]">
              {signal.rationale}
            </p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <SignalMetric
            icon={Activity}
            label="Confidence"
            tone="confidence"
            value={formatPercent(signal.confidence)}
          />
          <SignalMetric
            icon={TrendingUp}
            label="Risk / Reward"
            tone="info"
            value={signal.riskReward !== null ? signal.riskReward.toFixed(2) : "Pending"}
          />
          <SignalMetric
            icon={Target}
            label="Entry"
            tone="entry"
            value={formatPrice(signal.entryPrice, precision)}
          />
          <SignalMetric
            icon={ShieldCheck}
            label="Stop Loss"
            tone="stop"
            value={signal.stopLoss !== null ? formatPrice(signal.stopLoss, precision) : "Pending"}
          />
          <TargetsMetric precision={precision} signal={signal} />
          <SignalMetric
            icon={Activity}
            label="Timeframe"
            value={signal.timeframe.toUpperCase()}
          />
        </div>
      </CardContent>
    </Card>
  );
}

type SignalMetricProps = {
  icon: LucideIcon;
  label: string;
  tone?: "default" | "confidence" | "entry" | "info" | "stop" | "target";
  value: string;
};

function SignalMetric({ icon: Icon, label, tone = "default", value }: SignalMetricProps) {
  const toneClasses = {
    default: {
      container: "border-[var(--panel-border)] bg-[#0d131c]",
      icon: "text-[var(--gold)]",
      value: "text-[#fff8df]"
    },
    confidence: {
      container: "border-[#6f5620] bg-[#120f09]",
      icon: "text-[var(--gold)]",
      value: "text-[var(--gold-strong)]"
    },
    entry: {
      container: "border-[#6f5620] bg-[#120f09]",
      icon: "text-[var(--gold)]",
      value: "text-[#fff8df]"
    },
    info: {
      container: "border-[#234f86] bg-[var(--blue-soft)]",
      icon: "text-[var(--blue-strong)]",
      value: "text-[var(--blue-strong)]"
    },
    stop: {
      container: "border-[#6e2029] bg-[var(--red-soft)]",
      icon: "text-[var(--red-strong)]",
      value: "text-[#ff8787]"
    },
    target: {
      container: "border-[#1f6f49] bg-[#092016]",
      icon: "text-[#65d98d]",
      value: "text-[#7bea9b]"
    }
  } satisfies Record<NonNullable<SignalMetricProps["tone"]>, Record<"container" | "icon" | "value", string>>;
  const classes = toneClasses[tone];

  return (
    <div className={`rounded-lg border px-4 py-3 ${classes.container}`}>
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        <Icon className={`h-4 w-4 ${classes.icon}`} />
        {label}
      </div>
      <p className={`mt-2 text-base font-semibold leading-6 ${classes.value}`}>{value}</p>
    </div>
  );
}

function TargetsMetric({ precision, signal }: { precision: number; signal: Signal }) {
  return (
    <div className="rounded-lg border border-[#1f6f49] bg-[#092016] px-4 py-3 sm:col-span-2">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        <TrendingUp className="h-4 w-4 text-[#65d98d]" />
        Targets
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        {signal.targets.length > 0 ? (
          signal.targets.map((target) => (
            <div
              className="flex items-center justify-between gap-3 rounded-md border border-[#2c8155] bg-[#0d2a1b] px-3 py-2"
              key={target.label}
            >
              <span className="text-xs font-semibold uppercase tracking-wide text-[#b9d8c0]">
                {target.label}
              </span>
              <span className="text-sm font-semibold text-[#7bea9b]">
                {formatPrice(target.price, precision)}
              </span>
            </div>
          ))
        ) : (
          <p className="rounded-md border border-dashed border-[#2c8155] bg-[#0d2a1b] px-3 py-2 text-sm text-[#b9d8c0]">
            Pending
          </p>
        )}
      </div>
    </div>
  );
}
