"use client";

import { Clock3 } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { useNow } from "@/hooks/useNow";
import { formatRelativeTime } from "@/lib/formatters";

type ExpiryBadgeProps = {
  expiresAt: string | null;
};

const STALE_THRESHOLD_MS = 30 * 60 * 1000;

/**
 * A live freshness badge for a signal's `expires_at`: counts down while valid,
 * warns as it nears expiry, and flips to a danger state once stale.
 */
export function ExpiryBadge({ expiresAt }: ExpiryBadgeProps) {
  const now = useNow(1_000);

  if (expiresAt === null) {
    return <Badge tone="neutral">Open-ended</Badge>;
  }

  const expiryMs = new Date(expiresAt).getTime();

  // Pre-hydration: render a stable, neutral label without "ago/in" wording.
  if (now === null) {
    return (
      <Badge tone="neutral">
        <Clock3 className="mr-1.5 h-3.5 w-3.5" />
        Expiry tracked
      </Badge>
    );
  }

  const remaining = expiryMs - now;

  if (remaining <= 0) {
    return (
      <Badge tone="danger">
        <Clock3 className="mr-1.5 h-3.5 w-3.5" />
        Expired {formatRelativeTime(expiryMs, now)}
      </Badge>
    );
  }

  const tone = remaining <= STALE_THRESHOLD_MS ? "warning" : "info";

  return (
    <Badge tone={tone}>
      <Clock3 className="mr-1.5 h-3.5 w-3.5" />
      Expires {formatRelativeTime(expiryMs, now)}
    </Badge>
  );
}
