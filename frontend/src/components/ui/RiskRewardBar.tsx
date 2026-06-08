import { formatRiskReward } from "@/lib/formatters";
import { cn } from "@/lib/utils";

type RiskRewardBarProps = {
  /** Reward-to-risk ratio (reward / risk). Null renders a neutral "hold" bar. */
  ratio: number | null;
  className?: string;
};

/**
 * Visualises reward-to-risk as a split bar: a fixed red "1R" risk segment against
 * a green reward segment scaled to the ratio. Turns an abstract "2.4 : 1" into an
 * instantly legible "reward dwarfs the risk" (or doesn't) picture.
 */
export function RiskRewardBar({ ratio, className }: RiskRewardBarProps) {
  if (ratio === null || !Number.isFinite(ratio) || ratio <= 0) {
    return (
      <div className={cn("space-y-1.5", className)}>
        <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          <span>Reward : Risk</span>
          <span>Hold</span>
        </div>
        <div className="h-2 w-full rounded-full bg-[#1c2536]" />
      </div>
    );
  }

  // Reward share of the bar; cap the visual at 5R so an outlier doesn't crush the
  // risk segment to nothing.
  const capped = Math.min(ratio, 5);
  const rewardShare = capped / (capped + 1);
  const isHealthy = ratio >= 1.5;

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide">
        <span className="text-[var(--muted)]">Reward : Risk</span>
        <span className={isHealthy ? "text-[#7bea9b]" : "text-[var(--gold-strong)]"}>
          {formatRiskReward(ratio)} : 1
        </span>
      </div>
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-[#1c2536]">
        <div
          className="h-full bg-[var(--red)]"
          style={{ width: `${(1 - rewardShare) * 100}%` }}
        />
        <div
          className={cn("h-full", isHealthy ? "bg-[#2fb069]" : "bg-[var(--gold)]")}
          style={{ width: `${rewardShare * 100}%`, transition: "width 500ms ease-out" }}
        />
      </div>
    </div>
  );
}
