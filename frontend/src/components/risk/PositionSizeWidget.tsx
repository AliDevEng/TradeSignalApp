"use client";

import { useState } from "react";
import Link from "next/link";
import { Calculator, ChevronDown, Settings } from "lucide-react";

import { PositionSizeReadout } from "@/components/risk/PositionSizeReadout";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { isSignalSizeable, usePositionSizeQuery } from "@/hooks/usePositionSize";
import { cn } from "@/lib/utils";
import { isAccountConfigured, useAccountStore } from "@/store/accountStore";
import type { Signal } from "@/types/signal";

type PositionSizeWidgetProps = {
  signal: Signal;
  /**
   * `card` is a compact, collapsed-by-default disclosure (so list cards don't all
   * fire a sizing request at once); `detail` renders expanded immediately.
   */
  variant?: "card" | "detail";
};

/**
 * Position-size widget: turns the saved account (balance + risk %) and a signal's
 * entry/stop/targets into an exact, risk-bounded order via the backend
 * `POST /risk/position-size`. Shows a CTA to configure the account when it is
 * unset, and renders nothing for a signal that can't be sized (no stop, or a
 * neutral bias). The actual fetch is isolated in {@link SizedResult}, mounted only
 * when open + configured, so collapsed cards never touch React Query.
 */
export function PositionSizeWidget({ signal, variant = "card" }: PositionSizeWidgetProps) {
  const [open, setOpen] = useState(variant === "detail");
  const balance = useAccountStore((state) => state.balance);
  const riskPercent = useAccountStore((state) => state.riskPercent);

  if (!isSignalSizeable(signal)) {
    return null;
  }

  const configured = isAccountConfigured({ balance, riskPercent });

  return (
    <section
      aria-label="Position size"
      className="rounded-lg border border-[#263247] bg-[#0b111a] p-3"
    >
      {variant === "card" ? (
        <button
          aria-expanded={open}
          className="flex w-full items-center justify-between gap-2 text-left"
          onClick={() => setOpen((value) => !value)}
          type="button"
        >
          <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            <Calculator className="h-3.5 w-3.5 text-[var(--gold)]" />
            Position size
          </span>
          <ChevronDown
            className={cn("h-4 w-4 text-[var(--muted)] transition-transform", open && "rotate-180")}
          />
        </button>
      ) : (
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          <Calculator className="h-3.5 w-3.5 text-[var(--gold)]" />
          Position size
        </p>
      )}

      {open ? (
        <div className="mt-3">
          {configured ? (
            <SizedResult signal={signal} balance={balance} riskPercent={riskPercent} />
          ) : (
            <ConfigureAccountCta />
          )}
        </div>
      ) : null}
    </section>
  );
}

function ConfigureAccountCta() {
  return (
    <div className="space-y-2">
      <p className="text-xs text-[var(--muted)]">
        Set your account balance and risk % to size this trade.
      </p>
      <Link
        className="inline-flex items-center gap-1.5 rounded-md border border-[#263247] bg-[#101722] px-3 py-1.5 text-xs font-semibold text-[var(--gold-strong)] transition-colors hover:text-[#fff8df]"
        href="/settings"
      >
        <Settings className="h-3.5 w-3.5" />
        Configure account
      </Link>
    </div>
  );
}

function SizedResult({
  signal,
  balance,
  riskPercent
}: {
  signal: Signal;
  balance: number;
  riskPercent: number;
}) {
  const query = usePositionSizeQuery(signal, balance, riskPercent);

  if (query.isPending) {
    return <LoadingSpinner label="Sizing…" />;
  }
  if (query.isError || !query.data) {
    return (
      <p className="text-xs text-[#ffb4b4]">
        Couldn’t size this position right now. Try again shortly.
      </p>
    );
  }
  return <PositionSizeReadout result={query.data} />;
}
