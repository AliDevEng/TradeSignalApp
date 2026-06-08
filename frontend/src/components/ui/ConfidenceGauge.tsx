import { cn } from "@/lib/utils";

type ConfidenceGaugeProps = {
  /** Confidence as a fraction in [0, 1]. */
  value: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
};

/**
 * A radial progress ring for model confidence. The arc colour shifts with the
 * confidence tier (gold = high, blue = moderate, muted = low) so the number reads
 * at a glance from across the room — the at-a-glance "how much do I trust this"
 * cue that anchors the hero setup.
 */
export function ConfidenceGauge({
  value,
  size = 132,
  strokeWidth = 10,
  className
}: ConfidenceGaugeProps) {
  const clamped = Math.max(0, Math.min(1, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dash = circumference * clamped;
  const percent = Math.round(clamped * 100);

  const tier =
    clamped >= 0.7
      ? { stroke: "var(--gold-strong)", text: "text-[var(--gold-strong)]" }
      : clamped >= 0.55
        ? { stroke: "var(--blue-strong)", text: "text-[var(--blue-strong)]" }
        : { stroke: "#7f8da3", text: "text-[#9aa4b2]" };

  return (
    <div
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: size, height: size }}
    >
      <svg className="-rotate-90" height={size} width={size} aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          fill="none"
          r={radius}
          stroke="#1c2536"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          fill="none"
          r={radius}
          stroke={tier.stroke}
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
          strokeWidth={strokeWidth}
          style={{ transition: "stroke-dasharray 600ms cubic-bezier(0.22, 1, 0.36, 1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("text-2xl font-bold leading-none", tier.text)}>{percent}%</span>
        <span className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          Confidence
        </span>
      </div>
    </div>
  );
}
