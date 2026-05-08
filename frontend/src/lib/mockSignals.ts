import type { Signal, SignalStats, TradingPair } from "@/types/signal";

export const tradingPairs: TradingPair[] = [
  {
    id: 1,
    symbol: "XAUUSD",
    baseCurrency: "XAU",
    quoteCurrency: "USD",
    displayName: "Gold / US Dollar",
    isActive: true
  },
  {
    id: 2,
    symbol: "EURUSD",
    baseCurrency: "EUR",
    quoteCurrency: "USD",
    displayName: "Euro / US Dollar",
    isActive: true
  },
  {
    id: 3,
    symbol: "GBPUSD",
    baseCurrency: "GBP",
    quoteCurrency: "USD",
    displayName: "British Pound / US Dollar",
    isActive: true
  },
  {
    id: 4,
    symbol: "USDJPY",
    baseCurrency: "USD",
    quoteCurrency: "JPY",
    displayName: "US Dollar / Japanese Yen",
    isActive: false
  }
];

export const signals: Signal[] = [
  {
    id: "sig-xauusd-1",
    pairId: 1,
    symbol: "XAUUSD",
    displayName: "Gold / US Dollar",
    direction: "buy",
    status: "active",
    confidence: 0.84,
    entryPrice: 2368.42,
    stopLoss: 2354.8,
    takeProfit: 2396.2,
    timeframe: "1h",
    generatedAt: "2026-05-08T10:35:00.000Z",
    expiresAt: "2026-05-08T16:35:00.000Z",
    riskReward: 2.04,
    rationale:
      "Momentum reclaimed the prior London range while volatility compresses above VWAP. Continuation is preferred while price holds the liquidity shelf."
  },
  {
    id: "sig-eurusd-1",
    pairId: 2,
    symbol: "EURUSD",
    displayName: "Euro / US Dollar",
    direction: "sell",
    status: "active",
    confidence: 0.76,
    entryPrice: 1.08342,
    stopLoss: 1.0871,
    takeProfit: 1.0759,
    timeframe: "1h",
    generatedAt: "2026-05-08T09:50:00.000Z",
    expiresAt: "2026-05-08T15:50:00.000Z",
    riskReward: 2.04,
    rationale:
      "Trend structure remains heavy below the session pivot. A failed retest opens room toward the lower value area if dollar strength persists."
  },
  {
    id: "sig-gbpusd-1",
    pairId: 3,
    symbol: "GBPUSD",
    displayName: "British Pound / US Dollar",
    direction: "neutral",
    status: "watchlist",
    confidence: 0.61,
    entryPrice: 1.27125,
    stopLoss: null,
    takeProfit: null,
    timeframe: "4h",
    generatedAt: "2026-05-08T08:15:00.000Z",
    expiresAt: "2026-05-08T20:15:00.000Z",
    riskReward: null,
    rationale:
      "Price is balanced between weekly liquidity zones. Waiting for a clean break protects capital until directional conviction improves."
  },
  {
    id: "sig-usdjpy-1",
    pairId: 4,
    symbol: "USDJPY",
    displayName: "US Dollar / Japanese Yen",
    direction: "buy",
    status: "expired",
    confidence: 0.69,
    entryPrice: 155.82,
    stopLoss: 155.32,
    takeProfit: 156.74,
    timeframe: "1h",
    generatedAt: "2026-05-07T20:10:00.000Z",
    expiresAt: "2026-05-08T02:10:00.000Z",
    riskReward: 1.84,
    rationale:
      "The setup lost freshness after Asia session range expansion. Keep it archived for model review, not execution."
  }
];

export const signalStats: SignalStats = {
  activeSignals: 2,
  averageConfidence: 0.73,
  modelWinRate: 0.68,
  monitoredPairs: tradingPairs.filter((pair) => pair.isActive).length,
  analysisCadenceMinutes: 15,
  monthlySignalVolume: 1280
};
