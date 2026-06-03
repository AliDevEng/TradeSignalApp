import type { IndicatorSnapshot, Signal } from "@/types/signal";

export type SignalPriceLevelTone = "entry" | "stop" | "target";

export type SignalPriceLevel = {
  id: string;
  label: string;
  price: number;
  tone: SignalPriceLevelTone;
  /** Signed distance from entry, as a fraction. Null for the entry itself. */
  distancePercent: number | null;
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
      tone: "entry",
      distancePercent: null
    }
  ];

  if (signal.stopLoss !== null) {
    levels.push({
      id: `${signal.id}-stop`,
      label: "Stop Loss",
      price: signal.stopLoss,
      tone: "stop",
      distancePercent: signal.stopDistancePercent
    });
  }

  signal.targets.forEach((target) => {
    levels.push({
      id: `${signal.id}-${target.label.toLowerCase()}`,
      label: target.label,
      price: target.price,
      tone: "target",
      distancePercent: target.distancePercent
    });
  });

  return levels;
}

export type IndicatorReferenceLabel = "EMA20" | "EMA50" | "EMA200" | "BB Upper" | "BB Lower";

export type IndicatorReferenceLevel = {
  id: string;
  label: IndicatorReferenceLabel;
  price: number;
};

/**
 * Indicator-derived price levels that share the signal's price axis (moving
 * averages and Bollinger bands). These give the level-map chart real market
 * context without needing an OHLCV history feed.
 */
export function getIndicatorReferenceLevels(
  signalId: string,
  indicators: IndicatorSnapshot | null
): IndicatorReferenceLevel[] {
  if (indicators === null) {
    return [];
  }

  const candidates: Array<[IndicatorReferenceLabel, number | null]> = [
    ["BB Upper", indicators.bbUpper],
    ["EMA20", indicators.ema20],
    ["EMA50", indicators.ema50],
    ["EMA200", indicators.ema200],
    ["BB Lower", indicators.bbLower]
  ];

  return candidates.flatMap(([label, price]) =>
    price === null ? [] : [{ id: `${signalId}-${label}`, label, price }]
  );
}
