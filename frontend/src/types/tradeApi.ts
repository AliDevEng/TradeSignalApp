export type ApiSignalDirection = "buy" | "sell" | "neutral";
export type ApiAnalysisRunStatus = "pending" | "running" | "success" | "partial" | "failed";
export type ApiAnalysisRunTrigger = "scheduler" | "manual";

export type ApiPair = {
  id: number;
  symbol: string;
  base_currency: string;
  quote_currency: string;
  display_name: string | null;
  is_active: boolean;
};

/**
 * The indicator values the backend persists verbatim into
 * `signals.indicators_snapshot` (JSONB). Mirrors the backend `IndicatorSnapshot`
 * (see `services/indicators/calculator.py`). Every numeric field is nullable
 * because the series may have been too short for that indicator's window.
 */
export type ApiIndicatorSnapshot = {
  as_of: string | null;
  candles_analyzed: number;
  last_close: number | null;
  sma_20: number | null;
  sma_50: number | null;
  ema_20: number | null;
  ema_50: number | null;
  ema_200: number | null;
  rsi_14: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  atr_14: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  bb_percent: number | null;
};

export type ApiSignal = {
  id: string;
  pair_id: number;
  pair_symbol: string | null;
  analysis_run_id: string | null;
  direction: ApiSignalDirection;
  confidence: number;
  entry_price: string;
  stop_loss: string | null;
  // The take-profit ladder, ordered TP1..TP3. `take_profit` is the primary
  // target (TP1); the secondary scale-out targets are nullable.
  take_profit: string | null;
  take_profit_2: string | null;
  take_profit_3: string | null;
  timeframe: string;
  rationale: string | null;
  indicators_snapshot: Record<string, unknown> | null;
  generated_at: string;
  expires_at: string | null;
  ai_provider: string | null;
  ai_model: string | null;
};

export type ApiAnalysisRun = {
  id: string;
  status: ApiAnalysisRunStatus;
  trigger: ApiAnalysisRunTrigger;
  timeframe: string;
  candle_count: number;
  started_at: string;
  finished_at: string | null;
  pairs_processed: number;
  pairs_failed: number;
  ai_provider: string | null;
  ai_model: string | null;
  error_message: string | null;
};
