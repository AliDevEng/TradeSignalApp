"use client";

import { useState } from "react";
import { RotateCcw, Wallet } from "lucide-react";

import { OpenRiskMeter } from "@/components/risk/OpenRiskMeter";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { isSignalSizeable } from "@/hooks/usePositionSize";
import { formatCurrency } from "@/lib/formatters";
import { useAccountStore } from "@/store/accountStore";
import type { Signal } from "@/types/signal";

type AccountRiskCardProps = {
  signals: Signal[];
};

/**
 * The dashboard's live Account & Risk control. Editing the balance or risk %
 * writes straight to the store on change (no Save button) so every signal's lot
 * size and the open-risk meter recompute instantly — the "change balance, sizing
 * updates everywhere" behaviour the desk is built around. Local string state lets
 * the field be cleared mid-edit without snapping the store to 0.
 */
export function AccountRiskCard({ signals }: AccountRiskCardProps) {
  const balance = useAccountStore((state) => state.balance);
  const riskPercent = useAccountStore((state) => state.riskPercent);
  const capPercent = useAccountStore((state) => state.dailyRiskCapPercent);
  const setBalance = useAccountStore((state) => state.setBalance);
  const setRiskPercent = useAccountStore((state) => state.setRiskPercent);
  const clear = useAccountStore((state) => state.clear);

  const [balanceInput, setBalanceInput] = useState(() => (balance > 0 ? String(balance) : ""));
  const [riskInput, setRiskInput] = useState(() => (riskPercent > 0 ? String(riskPercent) : ""));
  // Reconcile external store changes (rehydration, the command-bar pill) into the
  // fields without clobbering an in-progress edit — React's "adjust state during
  // render" pattern, which the hooks lint prefers over a setState-in-effect.
  const [syncedBalance, setSyncedBalance] = useState(balance);
  const [syncedRisk, setSyncedRisk] = useState(riskPercent);

  if (balance !== syncedBalance) {
    setSyncedBalance(balance);
    setBalanceInput(balance > 0 ? String(balance) : "");
  }
  if (riskPercent !== syncedRisk) {
    setSyncedRisk(riskPercent);
    setRiskInput(riskPercent > 0 ? String(riskPercent) : "");
  }

  const sizeableActiveCount = signals.filter(
    (signal) => signal.status === "active" && isSignalSizeable(signal)
  ).length;
  const riskAmountPerTrade = balance > 0 ? (riskPercent / 100) * balance : 0;

  return (
    <Card id="account">
      <CardHeader className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Wallet className="h-4 w-4 text-[var(--gold)]" />
          <h2 className="text-sm font-semibold text-[#fff8df]">Account &amp; risk</h2>
        </div>
        {balance > 0 ? (
          <button
            className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--muted)] transition-colors hover:text-[#fff8df]"
            onClick={clear}
            type="button"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </button>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              Balance ($)
            </span>
            <input
              className="mt-1.5 w-full rounded-md border border-[#263247] bg-[#0d131c] px-3 py-2 text-sm font-semibold text-[#fff8df] outline-none focus:border-[var(--gold)]"
              inputMode="decimal"
              onChange={(event) => {
                setBalanceInput(event.target.value);
                const next = Number(event.target.value);
                const resolved = Number.isFinite(next) && next > 0 ? next : 0;
                setSyncedBalance(resolved);
                setBalance(resolved);
              }}
              placeholder="10,000"
              step="any"
              type="number"
              value={balanceInput}
            />
          </label>
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              Risk / trade (%)
            </span>
            <input
              className="mt-1.5 w-full rounded-md border border-[#263247] bg-[#0d131c] px-3 py-2 text-sm font-semibold text-[#fff8df] outline-none focus:border-[var(--gold)]"
              inputMode="decimal"
              max={100}
              min={0}
              onChange={(event) => {
                setRiskInput(event.target.value);
                const next = Number(event.target.value);
                const resolved = Number.isFinite(next) && next > 0 ? Math.min(next, 100) : 0;
                setSyncedRisk(resolved);
                setRiskPercent(resolved);
              }}
              placeholder="1"
              step="any"
              type="number"
              value={riskInput}
            />
          </label>
        </div>

        {balance > 0 ? (
          <p className="text-xs text-[var(--muted)]">
            Risking{" "}
            <span className="font-semibold text-[#ffb4b4]">
              {formatCurrency(riskAmountPerTrade)}
            </span>{" "}
            per trade. Lot sizes update live across every signal.
          </p>
        ) : (
          <p className="text-xs text-[var(--muted)]">
            Stored only in this browser — never sent to any account. Set a balance to size every
            setup.
          </p>
        )}

        <OpenRiskMeter
          balance={balance}
          capPercent={capPercent}
          riskPercent={riskPercent}
          sizeableActiveCount={sizeableActiveCount}
        />
      </CardContent>
    </Card>
  );
}
