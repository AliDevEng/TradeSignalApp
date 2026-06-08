"use client";

import Link from "next/link";
import { Calculator, Loader2 } from "lucide-react";

import { isSignalSizeable, usePositionSizeQuery } from "@/hooks/usePositionSize";
import { formatCurrency } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import { isAccountConfigured, useAccountStore } from "@/store/accountStore";
import type { Signal } from "@/types/signal";

type LiveLotSizeProps = {
  signal: Signal;
  /** `inline` is a single compact row for list cards; `panel` is a richer block for the hero. */
  variant?: "inline" | "panel";
  className?: string;
};

/**
 * Always-live position sizing for a signal. Unlike the collapsible
 * {@link PositionSizeWidget}, this stays mounted and recomputes the instant the
 * account balance or risk % changes (the query is keyed on both), so editing the
 * balance pill updates every card's lots in real time. Renders a subtle CTA when
 * the account is unset and nothing when the signal can't be sized.
 */
export function LiveLotSize({ signal, variant = "inline", className }: LiveLotSizeProps) {
  const balance = useAccountStore((state) => state.balance);
  const riskPercent = useAccountStore((state) => state.riskPercent);

  if (!isSignalSizeable(signal)) {
    return null;
  }

  if (!isAccountConfigured({ balance, riskPercent })) {
    return (
      <Link
        className={cn(
          "flex items-center gap-2 rounded-lg border border-dashed border-[#3a4761] bg-[#0b111a] px-3 py-2 text-xs font-semibold text-[var(--gold-strong)] transition-colors hover:border-[var(--gold)]",
          className
        )}
        href="/dashboard#account"
      >
        <Calculator className="h-3.5 w-3.5" />
        Set your balance to size this trade
      </Link>
    );
  }

  return (
    <SizedReadout
      balance={balance}
      className={className}
      riskPercent={riskPercent}
      signal={signal}
      variant={variant}
    />
  );
}

function SizedReadout({
  signal,
  balance,
  riskPercent,
  variant,
  className
}: {
  signal: Signal;
  balance: number;
  riskPercent: number;
  variant: "inline" | "panel";
  className?: string;
}) {
  const query = usePositionSizeQuery(signal, balance, riskPercent);

  const lots =
    query.data && query.data.lots > 0
      ? new Intl.NumberFormat("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        }).format(query.data.lots)
      : query.data
        ? "—"
        : null;

  if (variant === "panel") {
    return (
      <div
        className={cn(
          "grid grid-cols-3 gap-2 rounded-lg border border-[#263247] bg-[#0b111a] p-3",
          className
        )}
      >
        <PanelMetric
          label="Lots"
          tone="gold"
          value={query.isPending ? "…" : (lots ?? "—")}
        />
        <PanelMetric
          label="Risk"
          tone="red"
          value={
            query.data ? formatCurrency(query.data.riskAmount, query.data.quoteCurrency) : "…"
          }
        />
        <PanelMetric
          label="Notional"
          value={
            query.data
              ? formatCurrency(query.data.positionValue, query.data.quoteCurrency)
              : "…"
          }
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-2 rounded-lg border border-[#263247] bg-[#0b111a] px-3 py-2",
        className
      )}
    >
      <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
        <Calculator className="h-3.5 w-3.5 text-[var(--gold)]" />
        Position
      </span>
      {query.isPending ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--muted)]" />
      ) : query.isError || !query.data ? (
        <span className="text-xs text-[var(--muted)]">unavailable</span>
      ) : (
        <span className="flex items-center gap-3 text-sm font-semibold">
          <span className="text-[var(--gold-strong)]">{lots} lots</span>
          <span className="text-[#ffb4b4]">
            {formatCurrency(query.data.riskAmount, query.data.quoteCurrency)} risk
          </span>
        </span>
      )}
    </div>
  );
}

function PanelMetric({
  label,
  value,
  tone = "default"
}: {
  label: string;
  value: string;
  tone?: "default" | "gold" | "red";
}) {
  const valueClass =
    tone === "gold"
      ? "text-[var(--gold-strong)]"
      : tone === "red"
        ? "text-[#ffb4b4]"
        : "text-[#fff8df]";
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
        {label}
      </p>
      <p className={cn("mt-1 truncate text-base font-semibold", valueClass)}>{value}</p>
    </div>
  );
}
