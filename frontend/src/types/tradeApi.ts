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

export type ApiSignal = {
  id: string;
  pair_id: number;
  pair_symbol: string | null;
  analysis_run_id: string | null;
  direction: ApiSignalDirection;
  confidence: number;
  entry_price: string;
  stop_loss: string | null;
  take_profit: string | null;
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
