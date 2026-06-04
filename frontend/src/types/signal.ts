export type SignalDirection = "buy" | "sell" | "neutral";
export type SignalTradeStyle = "scalp" | "swing";
export type SignalStatus = "active" | "watchlist" | "expired";
export type Timeframe = "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "1d";

/**
 * What price did after the signal was generated — the backend outcome
 * vocabulary (see `models/signal.py::SignalOutcome`). `open` until the outcome
 * evaluator finds a terminal result.
 */
export type SignalOutcome =
  | "open"
  | "hit_tp1"
  | "hit_tp2"
  | "hit_tp3"
  | "hit_sl"
  | "expired"
  | "cancelled";

export type SignalTargetLabel = "TP1" | "TP2" | "TP3";

export type SignalTarget = {
  label: SignalTargetLabel;
  price: number;
  /** Signed distance from entry, as a fraction (e.g. 0.012 = +1.2%). */
  distancePercent: number | null;
};

export type SignalReasoning = {
  thesis: string;
  confirmations: string[];
  riskPlan: string;
  invalidation: string;
  executionNotes: string[];
};

/**
 * Technical indicators captured at signal-generation time. A normalised,
 * UI-facing mirror of the backend `indicators_snapshot` JSONB payload.
 */
export type IndicatorSnapshot = {
  asOf: string | null;
  candlesAnalyzed: number;
  lastClose: number | null;
  sma20: number | null;
  sma50: number | null;
  ema20: number | null;
  ema50: number | null;
  ema200: number | null;
  rsi14: number | null;
  macd: number | null;
  macdSignal: number | null;
  macdHistogram: number | null;
  atr14: number | null;
  bbUpper: number | null;
  bbMiddle: number | null;
  bbLower: number | null;
  bbPercent: number | null;
};

export type TradingPair = {
  id: number;
  symbol: string;
  baseCurrency: string;
  quoteCurrency: string;
  displayName: string;
  isActive: boolean;
};

export type Signal = {
  id: string;
  pairId: number;
  analysisRunId: string | null;
  symbol: string;
  displayName: string;
  direction: SignalDirection;
  tradeStyle: SignalTradeStyle;
  status: SignalStatus;
  confidence: number;
  entryPrice: number;
  stopLoss: number | null;
  /** Signed distance from entry to stop, as a fraction. Null without a stop. */
  stopDistancePercent: number | null;
  targets: SignalTarget[];
  timeframe: Timeframe;
  generatedAt: string;
  expiresAt: string | null;
  riskReward: number | null;
  rationale: string;
  reasoning: SignalReasoning;
  indicators: IndicatorSnapshot | null;
  aiProvider: string | null;
  aiModel: string | null;
  /** What happened after generation. `open` until the evaluator closes it. */
  outcome: SignalOutcome;
  /** Realised result in R multiples. Null while open or when risk is undefined. */
  realizedR: number | null;
  /** When the signal reached a terminal outcome (ISO 8601). Null while open. */
  closedAt: string | null;
};

export type SignalStats = {
  activeSignals: number;
  averageConfidence: number;
  modelWinRate: number;
  monitoredPairs: number;
  analysisCadenceMinutes: number;
  monthlySignalVolume: number;
};
