export type ApiSignalDirection = "buy" | "sell" | "neutral";
export type ApiSignalType = "scalp" | "swing";
export type ApiSignalOutcome =
  | "open"
  | "hit_tp1"
  | "hit_tp2"
  | "hit_tp3"
  | "hit_sl"
  | "expired"
  | "cancelled";
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
  signal_type: ApiSignalType;
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
  // Outcome tracking (backend Iteration 7). `realized_r` crosses the wire as a
  // Decimal string, like the other money/number fields.
  outcome: ApiSignalOutcome;
  realized_r: string | null;
  closed_at: string | null;
};

/**
 * Aggregated track record from `GET /api/v1/performance` (backend Iteration 8).
 * R figures cross the wire as Decimal strings, like every other money field;
 * ratios (`win_rate`, `avg_confidence`, `profit_factor`) are genuine statistics
 * and arrive as plain numbers. `profit_factor` is null when there is no losing R.
 */
export type ApiPerformanceSummary = {
  total: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_r: string;
  avg_r: string;
  profit_factor: number | null;
  gross_profit: string;
  gross_loss: string;
};

export type ApiCalibrationBucket = {
  label: string;
  lower: number;
  upper: number;
  count: number;
  avg_confidence: number;
  win_rate: number;
  wins: number;
};

export type ApiEquityPoint = {
  signal_id: string;
  closed_at: string;
  realized_r: string;
  cumulative_r: string;
};

export type ApiPerformance = {
  overall: ApiPerformanceSummary;
  by_type: Record<ApiSignalType, ApiPerformanceSummary>;
  calibration: ApiCalibrationBucket[];
  equity_curve: ApiEquityPoint[];
  generated_at: string;
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

/** Coarse pipeline state from `GET /api/v1/analysis/status`. */
export type ApiPipelineState = "idle" | "running" | "disabled";

/**
 * Live analysis-pipeline status backing the "next signal" UI. `next_run_at` is
 * the scheduler's authoritative next fire time (null when the scheduler is off
 * or has no upcoming run); `last_run` gives context for the idle/running copy.
 */
export type ApiPipelineStatus = {
  state: ApiPipelineState;
  interval_minutes: number;
  next_run_at: string | null;
  last_run: ApiAnalysisRun | null;
};
