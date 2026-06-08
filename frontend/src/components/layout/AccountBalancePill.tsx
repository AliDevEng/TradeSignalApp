"use client";

import { useEffect, useRef, useState } from "react";
import { Wallet } from "lucide-react";

import { formatCompactNumber } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import { useAccountStore } from "@/store/accountStore";

/**
 * The always-available account balance control in the command bar. Shows the
 * configured balance + risk % at a glance and opens a tiny popover to edit them
 * live — writes hit the store on every keystroke, so position sizing across the
 * whole app updates as the user types. Persisted client-side via the account
 * store; nothing leaves the browser.
 */
export function AccountBalancePill() {
  const balance = useAccountStore((state) => state.balance);
  const riskPercent = useAccountStore((state) => state.riskPercent);
  const setBalance = useAccountStore((state) => state.setBalance);
  const setRiskPercent = useAccountStore((state) => state.setRiskPercent);

  const [open, setOpen] = useState(false);
  const [balanceInput, setBalanceInput] = useState(() => (balance > 0 ? String(balance) : ""));
  const [riskInput, setRiskInput] = useState(() => (riskPercent > 0 ? String(riskPercent) : ""));
  // Track the last store value we reconciled so external changes (rehydration, the
  // dashboard card) resync the field, but the user's own keystrokes — including a
  // trailing "." mid-decimal — are never clobbered. This is React's documented
  // "adjust state during render" pattern, preferred over a setState-in-effect.
  const [syncedBalance, setSyncedBalance] = useState(balance);
  const [syncedRisk, setSyncedRisk] = useState(riskPercent);
  const containerRef = useRef<HTMLDivElement | null>(null);

  if (balance !== syncedBalance) {
    setSyncedBalance(balance);
    setBalanceInput(balance > 0 ? String(balance) : "");
  }
  if (riskPercent !== syncedRisk) {
    setSyncedRisk(riskPercent);
    setRiskInput(riskPercent > 0 ? String(riskPercent) : "");
  }

  useEffect(() => {
    if (!open) {
      return;
    }
    function onPointerDown(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const configured = balance > 0;

  return (
    <div className="relative" ref={containerRef}>
      <button
        aria-expanded={open}
        aria-haspopup="dialog"
        className={cn(
          "inline-flex h-9 items-center gap-2 rounded-md border px-2.5 text-xs font-semibold transition-colors",
          configured
            ? "border-[#6f5620] bg-[#191407] text-[var(--gold-strong)] hover:border-[var(--gold)]"
            : "border-[#293244] bg-[#101722] text-[var(--muted)] hover:text-[#fff8df]"
        )}
        onClick={() => setOpen((value) => !value)}
        type="button"
      >
        <Wallet className="h-4 w-4" />
        {configured ? (
          <span className="tabular-nums">
            ${formatCompactNumber(balance)}
            <span className="ml-1 text-[10px] text-[var(--muted)]">· {riskPercent}%</span>
          </span>
        ) : (
          <span className="hidden sm:inline">Set balance</span>
        )}
      </button>

      {open ? (
        <div
          aria-label="Account balance and risk"
          className="absolute right-0 z-40 mt-2 w-64 rounded-lg border border-[var(--panel-border)] bg-[#0d131c] p-4 shadow-[var(--surface-shadow)]"
          role="dialog"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            Account &amp; risk
          </p>
          <label className="mt-3 block">
            <span className="text-[11px] font-semibold text-[#fff8df]">Balance ($)</span>
            <input
              autoFocus
              className="mt-1 w-full rounded-md border border-[#263247] bg-[#0d131c] px-3 py-2 text-sm font-semibold text-[#fff8df] outline-none focus:border-[var(--gold)]"
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
          <label className="mt-3 block">
            <span className="text-[11px] font-semibold text-[#fff8df]">Risk per trade (%)</span>
            <input
              className="mt-1 w-full rounded-md border border-[#263247] bg-[#0d131c] px-3 py-2 text-sm font-semibold text-[#fff8df] outline-none focus:border-[var(--gold)]"
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
          <p className="mt-3 text-[11px] leading-4 text-[var(--muted)]">
            Used only to size positions. Stored in this browser — never sent anywhere.
          </p>
        </div>
      ) : null}
    </div>
  );
}
