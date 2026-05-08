import { Activity, ShieldCheck, Target, TrendingUp, type LucideIcon } from "lucide-react";

import { SignalBadge, SignalStatusBadge } from "@/components/signals/SignalBadge";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { formatPercent, formatPrice, getPricePrecision } from "@/lib/formatters";
import { getPrimaryTarget } from "@/lib/trading";
import type { Signal } from "@/types/signal";

type SignalSummaryPanelProps = {
  signal: Signal;
};

export function SignalSummaryPanel({ signal }: SignalSummaryPanelProps) {
  const precision = getPricePrecision(signal.symbol);
  const primaryTarget = getPrimaryTarget(signal);

  return (
    <Card>
      <CardHeader className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-2xl font-semibold text-[#fff8df]">{signal.symbol}</h2>
              <SignalBadge direction={signal.direction} />
              <SignalStatusBadge status={signal.status} />
            </div>
            <p className="mt-2 text-sm text-[var(--muted)]">{signal.displayName}</p>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[#c2cad6]">{signal.rationale}</p>
          </div>
          <div className="min-w-[128px] rounded-lg border border-[#6f5620] bg-[#120f09] px-4 py-3 text-right">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
              Confidence
            </p>
            <p className="mt-1 text-2xl font-semibold text-[var(--gold-strong)]">
              {formatPercent(signal.confidence)}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <SignalMetric icon={Target} label="Entry" value={formatPrice(signal.entryPrice, precision)} />
        <SignalMetric
          icon={ShieldCheck}
          label="Stop Loss"
          value={signal.stopLoss !== null ? formatPrice(signal.stopLoss, precision) : "Pending"}
        />
        <SignalMetric
          icon={TrendingUp}
          label="Primary Target"
          value={primaryTarget !== null ? formatPrice(primaryTarget, precision) : "Pending"}
        />
        <SignalMetric
          icon={Activity}
          label="Timeframe"
          value={signal.timeframe.toUpperCase()}
        />
        <SignalMetric
          icon={TrendingUp}
          label="Risk / Reward"
          value={signal.riskReward !== null ? signal.riskReward.toFixed(2) : "Pending"}
        />
      </CardContent>
    </Card>
  );
}

type SignalMetricProps = {
  icon: LucideIcon;
  label: string;
  value: string;
};

function SignalMetric({ icon: Icon, label, value }: SignalMetricProps) {
  return (
    <div className="rounded-lg border border-[var(--panel-border)] bg-[#0d131c] px-4 py-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        <Icon className="h-4 w-4 text-[var(--gold)]" />
        {label}
      </div>
      <p className="mt-2 text-base font-semibold leading-6 text-[#fff8df]">{value}</p>
    </div>
  );
}
