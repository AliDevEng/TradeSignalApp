export type SignalDirection = "buy" | "sell" | "neutral";
export type SignalStatus = "active" | "watchlist" | "expired";
export type Timeframe = "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "1d";

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
  symbol: string;
  displayName: string;
  direction: SignalDirection;
  status: SignalStatus;
  confidence: number;
  entryPrice: number;
  stopLoss: number | null;
  takeProfit: number | null;
  timeframe: Timeframe;
  generatedAt: string;
  expiresAt: string | null;
  riskReward: number | null;
  rationale: string;
};

export type SignalStats = {
  activeSignals: number;
  averageConfidence: number;
  modelWinRate: number;
  monitoredPairs: number;
  analysisCadenceMinutes: number;
  monthlySignalVolume: number;
};
