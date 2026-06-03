import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowLeft,
  Bot,
  CalendarClock,
  Clock3,
  Cpu,
  Radar,
  ShieldCheck,
  TrendingUp,
  type LucideIcon
} from "lucide-react";
import { notFound } from "next/navigation";

import { SignalLevelMap } from "@/components/charts/SignalLevelMap";
import { ExpiryBadge } from "@/components/signals/ExpiryBadge";
import { IndicatorsPanel } from "@/components/signals/IndicatorsPanel";
import { ReasoningPanel } from "@/components/signals/ReasoningPanel";
import { SignalSummaryPanel } from "@/components/signals/SignalSummaryPanel";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import {
  formatDateTime,
  formatPrice,
  formatSignedPercent,
  getPricePrecision
} from "@/lib/formatters";
import { getSignalById } from "@/lib/mockSignals";
import { mapApiPair, mapApiSignal } from "@/lib/signalMappers";
import { getPairs, getSignal } from "@/services/tradeService";
import type { Signal } from "@/types/signal";

type SignalDetailPageProps = {
  params: Promise<{
    signalId: string;
  }>;
};

export const metadata: Metadata = {
  title: "Signal detail",
  description:
    "Full trade plan: execution map, indicator snapshot, AI reasoning, freshness, and the take-profit ladder."
};

async function loadSignalDetail(signalId: string): Promise<Signal | null> {
  try {
    const [apiPairs, apiSignal] = await Promise.all([getPairs(), getSignal(signalId)]);
    const pairs = apiPairs.map(mapApiPair);

    return mapApiSignal(apiSignal, pairs);
  } catch {
    return getSignalById(signalId) ?? null;
  }
}

export default async function SignalDetailPage({ params }: SignalDetailPageProps) {
  const { signalId } = await params;
  const signal = await loadSignalDetail(signalId);

  if (!signal) {
    notFound();
  }

  const precision = getPricePrecision(signal.symbol);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--blue-strong)] transition-colors hover:text-[#8ab8ff]"
          href={`/pairs/${signal.symbol}`}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to pair view
        </Link>
        <h1 className="mt-4 text-3xl font-semibold text-[#fff8df]">Signal Detail</h1>
        <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
          Generated {formatDateTime(signal.generatedAt)} for {signal.displayName}
        </p>
      </div>

      <SignalSummaryPanel signal={signal} />

      <div className="grid gap-6 xl:grid-cols-[1.35fr_0.95fr]">
        <div className="space-y-6">
          <SignalLevelMap
            signal={signal}
            subtitle="Execution plan with entry, invalidation, and target ladder mapped against indicator reference levels."
            title={`${signal.symbol} execution map`}
          />

          <IndicatorsPanel indicators={signal.indicators} />

          <ReasoningPanel reasoning={signal.reasoning} />
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader className="space-y-3">
              <div className="flex items-center gap-2">
                <Radar className="h-4 w-4 text-[var(--gold)]" />
                <h2 className="text-lg font-semibold text-[#fff8df]">Execution Brief</h2>
              </div>
              <p className="text-sm leading-6 text-[var(--muted)]">
                Keep the trade plan readable at a glance: where the setup starts,
                where it fails, and how profit is distributed.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <ContextMetric
                  icon={Clock3}
                  label="Timeframe"
                  value={signal.timeframe.toUpperCase()}
                />
                <ContextMetric
                  icon={TrendingUp}
                  label="Risk / Reward"
                  value={signal.riskReward !== null ? signal.riskReward.toFixed(2) : "Pending"}
                />
                <ContextMetric
                  icon={CalendarClock}
                  label="Generated"
                  value={formatDateTime(signal.generatedAt)}
                />
                <ContextMetric
                  icon={Bot}
                  label="AI provider"
                  value={signal.aiProvider ?? "Unknown"}
                />
                <ContextMetric icon={Cpu} label="AI model" value={signal.aiModel ?? "Unknown"} />
                <div className="rounded-lg border border-[var(--panel-border)] bg-[#101722] px-4 py-3">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                    <ShieldCheck className="h-4 w-4 text-[var(--gold)]" />
                    Freshness
                  </div>
                  <div className="mt-2">
                    <ExpiryBadge expiresAt={signal.expiresAt} />
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-[var(--panel-border)] bg-[#0d131c] p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
                    Target Ladder
                  </h3>
                  <Badge tone="info">{signal.targets.length} levels</Badge>
                </div>
                <div className="mt-4 space-y-3">
                  <PriceLevel
                    emphasis="entry"
                    label="Entry"
                    value={formatPrice(signal.entryPrice, precision)}
                  />
                  <PriceLevel
                    distance={signal.stopDistancePercent}
                    emphasis="stop"
                    label="Stop Loss"
                    value={
                      signal.stopLoss !== null ? formatPrice(signal.stopLoss, precision) : "Pending"
                    }
                  />
                  {signal.targets.length > 0 ? (
                    signal.targets.map((target) => (
                      <PriceLevel
                        distance={target.distancePercent}
                        emphasis="target"
                        key={target.label}
                        label={target.label}
                        value={formatPrice(target.price, precision)}
                      />
                    ))
                  ) : (
                    <div className="rounded-lg border border-dashed border-[#45536a] bg-[#101722] px-4 py-5 text-sm text-[var(--muted)]">
                      No target ladder is defined yet for this signal.
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function PriceLevel({
  distance,
  emphasis,
  label,
  value
}: {
  distance?: number | null;
  emphasis: "entry" | "stop" | "target";
  label: string;
  value: string;
}) {
  const toneClasses = {
    entry: "border-[#6f5620] bg-[#120f09]",
    stop: "border-[#6e2029] bg-[var(--red-soft)]",
    target: "border-[#234f86] bg-[var(--blue-soft)]"
  } satisfies Record<"entry" | "stop" | "target", string>;

  return (
    <div
      className={`flex items-center justify-between gap-3 rounded-lg border px-4 py-3 ${toneClasses[emphasis]}`}
    >
      <span className="text-sm font-medium text-[var(--muted)]">{label}</span>
      <span className="flex items-baseline gap-2">
        {distance !== null && distance !== undefined ? (
          <span className="text-xs font-medium text-[var(--muted)]">
            {formatSignedPercent(distance)}
          </span>
        ) : null}
        <span className="text-sm font-semibold text-[#fff8df]">{value}</span>
      </span>
    </div>
  );
}

function ContextMetric({
  icon: Icon,
  label,
  value
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--panel-border)] bg-[#101722] px-4 py-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        <Icon className="h-4 w-4 text-[var(--gold)]" />
        {label}
      </div>
      <p className="mt-2 truncate text-sm font-semibold leading-6 text-[#fff8df]">{value}</p>
    </div>
  );
}
