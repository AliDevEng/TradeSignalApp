import { ShieldAlert, ShieldCheck } from "lucide-react";

import { formatCurrency } from "@/lib/formatters";
import { cn } from "@/lib/utils";

type OpenRiskMeterProps = {
  /** Number of active, sizeable setups currently in the queue. */
  sizeableActiveCount: number;
  balance: number;
  riskPercent: number;
  /** Soft ceiling on total open risk, as a percent of balance. */
  capPercent: number;
};

/**
 * "If you took every active setup at your configured risk" meter. By design each
 * trade risks `riskPercent` of balance, so planned open risk is simply
 * count × riskPercent — an honest, call-free projection of total exposure against
 * the daily cap. Warns (red) once the projection breaches the ceiling.
 */
export function OpenRiskMeter({
  sizeableActiveCount,
  balance,
  riskPercent,
  capPercent
}: OpenRiskMeterProps) {
  const openRiskPercent = sizeableActiveCount * riskPercent;
  const openRiskAmount = (openRiskPercent / 100) * balance;
  const capAmount = (capPercent / 100) * balance;
  const fill = capPercent > 0 ? Math.min(openRiskPercent / capPercent, 1) : 0;
  const breached = openRiskPercent > capPercent;

  return (
    <div className="rounded-lg border border-[#263247] bg-[#0b111a] p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          {breached ? (
            <ShieldAlert className="h-3.5 w-3.5 text-[var(--red-strong)]" />
          ) : (
            <ShieldCheck className="h-3.5 w-3.5 text-[#65d98d]" />
          )}
          Open risk if all taken
        </span>
        <span
          className={cn(
            "text-sm font-semibold",
            breached ? "text-[var(--red-strong)]" : "text-[#fff8df]"
          )}
        >
          {balance > 0 ? formatCurrency(openRiskAmount) : "—"}
          <span className="ml-1 text-xs text-[var(--muted)]">
            ({openRiskPercent.toFixed(1)}%)
          </span>
        </span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-[#1c2536]">
        <div
          className={cn("h-full rounded-full", breached ? "bg-[var(--red)]" : "bg-[#2fb069]")}
          style={{ width: `${fill * 100}%`, transition: "width 400ms ease-out" }}
        />
      </div>
      <p className="mt-1.5 text-[11px] text-[var(--muted)]">
        {sizeableActiveCount} active setup{sizeableActiveCount === 1 ? "" : "s"} · cap{" "}
        {capPercent}% {balance > 0 ? `(${formatCurrency(capAmount)})` : ""}
      </p>
    </div>
  );
}
