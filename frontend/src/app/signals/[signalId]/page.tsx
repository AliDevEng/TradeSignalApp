import Link from "next/link";
import {
  ArrowLeft,
  CalendarClock,
  Clock3,
  Radar,
  ShieldCheck,
  TrendingUp,
  type LucideIcon
} from "lucide-react";
import { notFound } from "next/navigation";

import { CandlestickChart } from "@/components/charts/CandlestickChart";
import { ReasoningPanel } from "@/components/signals/ReasoningPanel";
import { SignalSummaryPanel } from "@/components/signals/SignalSummaryPanel";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import {
  formatDateTime,
  formatPrice,
  getPricePrecision
} from "@/lib/formatters";
import { getSignalById, getCandlesForPair } from "@/lib/mockSignals";
import { mapApiPair, mapApiSignal } from "@/lib/signalMappers";
import { getPairs, getSignal } from "@/services/tradeService";
import type { Signal } from "@/types/signal";

type SignalDetailPageProps = {
  params: Promise<{
    signalId: string;
  }>;
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

  const candles = getCandlesForPair(signal.symbol);
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
            <CandlestickChart
              candles={candles}
              signal={signal}
              subtitle="Execution plan with entry, invalidation, and target ladder projected on the recent market structure."
              title={`${signal.symbol} execution map`}
            />

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
                    icon={ShieldCheck}
                    label="Expires"
                    value={signal.expiresAt ? formatDateTime(signal.expiresAt) : "Open-ended"}
                  />
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
                      emphasis="stop"
                      label="Stop Loss"
                      value={
                        signal.stopLoss !== null
                          ? formatPrice(signal.stopLoss, precision)
                          : "Pending"
                      }
                    />
                    {signal.targets.length > 0 ? (
                      signal.targets.map((target) => (
                        <PriceLevel
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
  emphasis,
  label,
  value
}: {
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
      <span className="text-sm font-semibold text-[#fff8df]">{value}</span>
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
      <p className="mt-2 text-sm font-semibold leading-6 text-[#fff8df]">{value}</p>
    </div>
  );
}
