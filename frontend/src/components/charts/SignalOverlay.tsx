"use client";

import { Badge } from "@/components/ui/Badge";
import { formatPrice, getPricePrecision } from "@/lib/formatters";
import { getSignalPriceLevels } from "@/lib/trading";
import { cn } from "@/lib/utils";
import type { Signal } from "@/types/signal";

type SignalOverlayProps = {
  signal: Signal;
  className?: string;
};

const toneClasses = {
  entry: "border-[#6f5620] bg-[#1b1508] text-[var(--gold-strong)]",
  stop: "border-[#6e2029] bg-[var(--red-soft)] text-[var(--red-strong)]",
  target: "border-[#234f86] bg-[var(--blue-soft)] text-[var(--blue-strong)]"
} as const;

export function SignalOverlay({ signal, className }: SignalOverlayProps) {
  const precision = getPricePrecision(signal.symbol);
  const levels = getSignalPriceLevels(signal);

  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {levels.map((level) => (
        <Badge className={toneClasses[level.tone]} key={level.id}>
          {level.label} {formatPrice(level.price, precision)}
        </Badge>
      ))}
    </div>
  );
}
