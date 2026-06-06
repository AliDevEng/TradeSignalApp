import { formatCurrency, formatRiskReward } from "@/lib/formatters";
import type { PositionSize } from "@/types/risk";

/**
 * Pure presentation of a sized position — lots, real risk, notional, and the
 * reward to each take-profit. Takes the already-fetched {@link PositionSize} so it
 * is trivially unit-testable; the data fetching + account wiring live in
 * {@link PositionSizeWidget}.
 */
export function PositionSizeReadout({ result }: { result: PositionSize }) {
  const lots = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(result.lots);

  if (result.lots <= 0) {
    return (
      <p className="rounded-md border border-[#5a4a20] bg-[#1a1407] px-3 py-2 text-xs text-[#e7cd86]">
        The risk budget ({formatCurrency(result.requestedRiskAmount, result.quoteCurrency)}) is too
        small for the minimum {result.minLot} lot at this stop distance. Increase the balance or
        risk %, or tighten the stop.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <Metric label="Lots" value={lots} tone="gold" />
        <Metric
          label="Risk"
          value={formatCurrency(result.riskAmount, result.quoteCurrency)}
          tone="red"
        />
        <Metric label="Units" value={new Intl.NumberFormat("en-US").format(result.units)} />
        <Metric
          label="Pip value"
          value={formatCurrency(result.pipValue, result.quoteCurrency)}
        />
      </div>

      {result.takeProfits.length > 0 ? (
        <div>
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Reward per target
          </p>
          <ul className="space-y-1">
            {result.takeProfits.map((tp, index) => (
              <li
                className="flex items-center justify-between gap-3 rounded-md bg-[#0d2a1b] px-2.5 py-1.5 text-xs"
                key={`${tp.price}-${index}`}
              >
                <span className="font-semibold text-[#b9d8c0]">TP{index + 1}</span>
                <span className="flex items-center gap-3">
                  <span className="text-[var(--blue-strong)]">
                    {formatRiskReward(tp.riskReward)} : 1
                  </span>
                  <span className="font-semibold text-[#7bea9b]">
                    +{formatCurrency(tp.profitAmount, result.quoteCurrency)}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function Metric({
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
    <div className="rounded-md border border-[#2a3445] bg-[#101722] px-2.5 py-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className={`mt-0.5 text-base font-semibold ${valueClass}`}>{value}</p>
    </div>
  );
}
