import { ArrowDownRight, ArrowRight, ArrowUpRight, Timer, Waypoints } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { SignalDirection, SignalStatus, SignalTradeStyle } from "@/types/signal";

type SignalBadgeProps = {
  direction: SignalDirection;
};

type SignalStatusBadgeProps = {
  status: SignalStatus;
};

type TradeStyleBadgeProps = {
  tradeStyle: SignalTradeStyle;
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
