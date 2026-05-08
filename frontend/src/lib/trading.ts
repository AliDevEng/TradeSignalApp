import type { Signal } from "@/types/signal";

export type SignalPriceLevelTone = "entry" | "stop" | "target";

export type SignalPriceLevel = {
  id: string;
  label: string;
  price: number;
  tone: SignalPriceLevelTone;
};

export function getPrimaryTarget(signal: Signal): number | null {
  return signal.targets[0]?.price ?? null;
}

export function getSignalPriceLevels(signal: Signal): SignalPriceLevel[] {
  const levels: SignalPriceLevel[] = [
    {
      id: `${signal.id}-entry`,
      label: "Entry",
      price: signal.entryPrice,
      tone: "entry"
    }
  ];

  if (signal.stopLoss !== null) {
    levels.push({
      id: `${signal.id}-stop`,
      label: "Stop Loss",
      price: signal.stopLoss,
      tone: "stop"
    });
  }

  signal.targets.forEach((target) => {
    levels.push({
      id: `${signal.id}-${target.label.toLowerCase()}`,
      label: target.label,
      price: target.price,
      tone: "target"
    });
  });

  return levels;
}
