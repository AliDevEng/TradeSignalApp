import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CheckCheck,
  CircleDot,
  Hourglass,
  Timer,
  Waypoints,
  X,
  type LucideIcon
} from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import { describeOutcome, type OutcomeCategory } from "@/lib/outcome";
import type {
  SignalDirection,
  SignalOutcome,
  SignalStatus,
  SignalTradeStyle
} from "@/types/signal";

type SignalBadgeProps = {
  direction: SignalDirection;
};

type SignalStatusBadgeProps = {
  status: SignalStatus;
};

type TradeStyleBadgeProps = {
  tradeStyle: SignalTradeStyle;
};

type OutcomeBadgeProps = {
  outcome: SignalOutcome;
  realizedR: number | null;
  className?: string;
};

const directionConfig = {
  buy: {
    label: "Buy",
    icon: ArrowUpRight,
    tone: "success"
  },
  sell: {
    label: "Sell",
    icon: ArrowDownRight,
    tone: "danger"
  },
  neutral: {
    label: "Neutral",
    icon: ArrowRight,
    tone: "warning"
  }
} as const;

const statusConfig = {
  active: {
    label: "Active",
    tone: "success"
  },
  watchlist: {
    label: "Watchlist",
    tone: "warning"
  },
  expired: {
    label: "Expired",
    tone: "neutral"
  }
} as const;

const tradeStyleConfig = {
  scalp: {
    label: "Scalp",
    icon: Timer,
    tone: "info"
  },
  swing: {
    label: "Swing",
    icon: Waypoints,
    tone: "neutral"
  }
} as const;

export function SignalBadge({ direction }: SignalBadgeProps) {
  const config = directionConfig[direction];
  const Icon = config.icon;

  return (
    <Badge tone={config.tone}>
      <Icon className="mr-1.5 h-3.5 w-3.5" />
      {config.label}
    </Badge>
  );
}

export function SignalStatusBadge({ status }: SignalStatusBadgeProps) {
  const config = statusConfig[status];

  return <Badge tone={config.tone}>{config.label}</Badge>;
}

export function TradeStyleBadge({ tradeStyle }: TradeStyleBadgeProps) {
  const config = tradeStyleConfig[tradeStyle];
  const Icon = config.icon;

  return (
    <Badge tone={config.tone}>
      <Icon className="mr-1.5 h-3.5 w-3.5" />
      {config.label}
    </Badge>
  );
}

// The outcome badge uses the gold/green/red visual system directly rather than
// the 5-tone `Badge` (which has no green) so a win reads unmistakably positive.
const outcomeStyles: Record<OutcomeCategory, { className: string; icon: LucideIcon }> = {
  open: {
    className: "border-[#6f5620] bg-[var(--gold-soft)] text-[var(--gold-strong)]",
    icon: CircleDot
  },
  win: { className: "border-[#1f6f49] bg-[#092016] text-[#7bea9b]", icon: CheckCheck },
  loss: { className: "border-[#6e2029] bg-[var(--red-soft)] text-[var(--red-strong)]", icon: X },
  expired: { className: "border-[#344053] bg-[#141b27] text-[#cbd5e1]", icon: Hourglass }
};

export function OutcomeBadge({ outcome, realizedR, className }: OutcomeBadgeProps) {
  const { category, text } = describeOutcome(outcome, realizedR);
  const style = outcomeStyles[category];
  const Icon = style.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide",
        style.className,
        className
      )}
    >
      <Icon className="mr-1.5 h-3.5 w-3.5" />
      {text}
    </span>
  );
}
