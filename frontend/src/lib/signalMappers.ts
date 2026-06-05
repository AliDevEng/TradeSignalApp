import type { ApiIndicatorSnapshot, ApiPair, ApiSignal } from "@/types/tradeApi";
import type {
  IndicatorSnapshot,
  Signal,
  SignalOutcome,
  SignalReasoning,
  SignalStatus,
  SignalTarget,
  SignalTargetLabel,
  SignalTradeStyle,
  Timeframe,
  TradingPair
} from "@/types/signal";

const timeframeFallback: Timeframe = "1h";
const supportedTimeframes = new Set<Timeframe>(["1m", "5m", "15m", "30m", "1h", "4h", "1d"]);
const tradeStyleFallback: SignalTradeStyle = "swing";
const supportedTradeStyles = new Set<SignalTradeStyle>(["scalp", "swing"]);
const outcomeFallback: SignalOutcome = "open";
const supportedOutcomes = new Set<SignalOutcome>([
  "open",
  "hit_tp1",
  "hit_tp2",
  "hit_tp3",
  "hit_sl",
  "expired",
  "cancelled"
]);

function normalizeOutcome(value: string | null | undefined): SignalOutcome {
  return value && supportedOutcomes.has(value as SignalOutcome)
    ? (value as SignalOutcome)
    : outcomeFallback;
}

function normalizeTradeStyle(value: string | null | undefined): SignalTradeStyle {
  return value && supportedTradeStyles.has(value as SignalTradeStyle)
    ? (value as SignalTradeStyle)
    : tradeStyleFallback;
}

function parsePrice(value: string | null): number | null {
  if (value === null) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseNumber(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return null;
  }

  return value;
}

function parseString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function normalizeTimeframe(value: string): Timeframe {
  return supportedTimeframes.has(value as Timeframe) ? (value as Timeframe) : timeframeFallback;
}

function deriveStatus(signal: ApiSignal): SignalStatus {
  if (signal.expires_at && new Date(signal.expires_at).getTime() < Date.now()) {
    return "expired";
  }

  return signal.direction === "neutral" ? "watchlist" : "active";
}

/** Signed distance from `entry` to `level`, as a fraction (0.012 = +1.2%). */
function distanceFromEntry(entry: number, level: number | null): number | null {
  if (level === null || entry === 0) {
    return null;
  }

  return (level - entry) / entry;
}

function buildTargets(signal: ApiSignal, entry: number): SignalTarget[] {
  const ladder: Array<{ label: SignalTargetLabel; value: string | null }> = [
    { label: "TP1", value: signal.take_profit },
    { label: "TP2", value: signal.take_profit_2 },
    { label: "TP3", value: signal.take_profit_3 }
  ];

  return ladder.flatMap(({ label, value }) => {
    const price = parsePrice(value);
    if (price === null) {
      return [];
    }

    return [{ label, price, distancePercent: distanceFromEntry(entry, price) }];
  });
}

/**
 * Risk-to-reward for the first target, computed with direction-aware *signed*
 * distances. Returns null when the geometry contradicts the direction (a buy
 * whose stop sits above entry, or whose target sits below it — and the reverse
 * for a sell) instead of masking it with `Math.abs`, so a broken signal shows
 * "—" rather than a plausible-looking ratio.
 */
function computeRiskReward(
  direction: ApiSignal["direction"],
  entry: number,
  stopLoss: number | null,
  firstTarget: number | null
): number | null {
  if (stopLoss === null || firstTarget === null) {
    return null;
  }

  let risk: number;
  let reward: number;
  if (direction === "buy") {
    risk = entry - stopLoss;
    reward = firstTarget - entry;
  } else if (direction === "sell") {
    risk = stopLoss - entry;
    reward = entry - firstTarget;
  } else {
    return null; // neutral has no actionable R:R
  }

  if (risk <= 0 || reward <= 0) {
    return null; // levels inconsistent with the stated direction
  }

  return reward / risk;
}

function mapIndicators(raw: Record<string, unknown> | null): IndicatorSnapshot | null {
  if (raw === null) {
    return null;
  }

  const snapshot = raw as Partial<ApiIndicatorSnapshot>;

  return {
    asOf: parseString(snapshot.as_of),
    candlesAnalyzed: parseNumber(snapshot.candles_analyzed) ?? 0,
    lastClose: parseNumber(snapshot.last_close),
    sma20: parseNumber(snapshot.sma_20),
    sma50: parseNumber(snapshot.sma_50),
    ema20: parseNumber(snapshot.ema_20),
    ema50: parseNumber(snapshot.ema_50),
    ema200: parseNumber(snapshot.ema_200),
    rsi14: parseNumber(snapshot.rsi_14),
    macd: parseNumber(snapshot.macd),
    macdSignal: parseNumber(snapshot.macd_signal),
    macdHistogram: parseNumber(snapshot.macd_histogram),
    atr14: parseNumber(snapshot.atr_14),
    bbUpper: parseNumber(snapshot.bb_upper),
    bbMiddle: parseNumber(snapshot.bb_middle),
    bbLower: parseNumber(snapshot.bb_lower),
    bbPercent: parseNumber(snapshot.bb_percent)
  };
}

function buildReasoning(signal: ApiSignal): SignalReasoning {
  const thesis = signal.rationale ?? "The backend returned this signal without a written rationale.";
  const indicators = signal.indicators_snapshot;
  const indicatorNames = indicators ? Object.keys(indicators).slice(0, 4) : [];

  return {
    thesis,
    confirmations:
      indicatorNames.length > 0
        ? indicatorNames.map((name) => `${name} was included in the model context.`)
        : ["Indicator details were not included with this signal."],
    riskPlan:
      signal.stop_loss !== null
        ? "Manage risk against the supplied stop loss and reassess if market structure changes."
        : "No stop loss was supplied, so this signal should stay in review mode before execution.",
    invalidation:
      signal.stop_loss !== null
        ? "The setup is invalidated if price accepts beyond the stop-loss level."
        : "Wait for a directional plan with explicit invalidation before acting.",
    executionNotes: [
      signal.ai_provider && signal.ai_model
        ? `Generated by ${signal.ai_provider}/${signal.ai_model}.`
        : "AI provider metadata was not supplied.",
      "Use fresh market context before placing real capital at risk."
    ]
  };
}

export function mapApiPair(pair: ApiPair): TradingPair {
  return {
    id: pair.id,
    symbol: pair.symbol,
    baseCurrency: pair.base_currency,
    quoteCurrency: pair.quote_currency,
    displayName: pair.display_name ?? `${pair.base_currency} / ${pair.quote_currency}`,
    isActive: pair.is_active
  };
}

export function mapApiSignal(signal: ApiSignal, pairs: TradingPair[]): Signal {
  const symbol = signal.pair_symbol ?? pairs.find((pair) => pair.id === signal.pair_id)?.symbol ?? "UNKNOWN";
  const pair = pairs.find((item) => item.symbol === symbol);
  const entryPrice = parsePrice(signal.entry_price) ?? 0;
  const stopLoss = parsePrice(signal.stop_loss);
  const targets = buildTargets(signal, entryPrice);

  return {
    id: signal.id,
    pairId: signal.pair_id,
    analysisRunId: signal.analysis_run_id,
    symbol,
    displayName: pair?.displayName ?? symbol,
    direction: signal.direction,
    tradeStyle: normalizeTradeStyle(signal.signal_type),
    status: deriveStatus(signal),
    confidence: signal.confidence,
    entryPrice,
    stopLoss,
    stopDistancePercent: distanceFromEntry(entryPrice, stopLoss),
    targets,
    timeframe: normalizeTimeframe(signal.timeframe),
    generatedAt: signal.generated_at,
    expiresAt: signal.expires_at,
    riskReward: computeRiskReward(signal.direction, entryPrice, stopLoss, targets[0]?.price ?? null),
    rationale: signal.rationale ?? "No rationale was supplied for this signal.",
    reasoning: buildReasoning(signal),
    indicators: mapIndicators(signal.indicators_snapshot),
    aiProvider: signal.ai_provider,
    aiModel: signal.ai_model,
    outcome: normalizeOutcome(signal.outcome),
    realizedR: parsePrice(signal.realized_r ?? null),
    closedAt: signal.closed_at ?? null
  };
}
