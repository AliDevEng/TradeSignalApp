import type {
  IndicatorSnapshot,
  Signal,
  SignalStats,
  SignalTarget,
  SignalTargetLabel,
  TradingPair
} from "@/types/signal";

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

/** Build a target ladder with entry-relative distances, mirroring the mapper. */
function ladder(entry: number, prices: Partial<Record<SignalTargetLabel, number>>): SignalTarget[] {
  return (Object.entries(prices) as Array<[SignalTargetLabel, number]>).map(([label, price]) => ({
    label,
    price,
    distancePercent: entry === 0 ? null : (price - entry) / entry
  }));
}

function distance(entry: number, level: number | null): number | null {
  return level === null || entry === 0 ? null : (level - entry) / entry;
}

const xauIndicators: IndicatorSnapshot = {
  asOf: "2026-05-08T10:00:00.000Z",
  candlesAnalyzed: 200,
  lastClose: 2367.9,
  sma20: 2361.4,
  sma50: 2352.8,
  ema20: 2362.7,
  ema50: 2354.1,
  ema200: 2338.5,
  rsi14: 63.4,
  macd: 4.21,
  macdSignal: 3.08,
  macdHistogram: 1.13,
  atr14: 6.82,
  bbUpper: 2374.2,
  bbMiddle: 2361.4,
  bbLower: 2348.6,
  bbPercent: 0.74
};

const eurIndicators: IndicatorSnapshot = {
  asOf: "2026-05-08T09:00:00.000Z",
  candlesAnalyzed: 200,
  lastClose: 1.0836,
  sma20: 1.0858,
  sma50: 1.0872,
  ema20: 1.0851,
  ema50: 1.0869,
  ema200: 1.0903,
  rsi14: 38.2,
  macd: -0.0011,
  macdSignal: -0.0007,
  macdHistogram: -0.0004,
  atr14: 0.0014,
  bbUpper: 1.0879,
  bbMiddle: 1.0858,
  bbLower: 1.0837,
  bbPercent: 0.18
};

export const signals: Signal[] = [
  {
    id: "sig-xauusd-1",
    pairId: 1,
    analysisRunId: "run-2026-05-08-1",
    symbol: "XAUUSD",
    displayName: "Gold / US Dollar",
    direction: "buy",
    tradeStyle: "swing",
    status: "active",
    confidence: 0.84,
    entryPrice: 2368.42,
    stopLoss: 2354.8,
    stopDistancePercent: distance(2368.42, 2354.8),
    targets: ladder(2368.42, { TP1: 2379.6, TP2: 2388.9, TP3: 2396.2 }),
    timeframe: "1h",
    generatedAt: "2026-05-08T10:35:00.000Z",
    expiresAt: "2026-05-08T16:35:00.000Z",
    riskReward: 2.04,
    rationale:
      "Momentum reclaimed the prior London range while volatility compresses above VWAP. Continuation is preferred while price holds the liquidity shelf.",
    reasoning: {
      thesis:
        "Bullish continuation is favored because price reclaimed intraday structure and held above the last impulsive breakout base.",
      confirmations: [
        "Session high was recovered with expanding candle bodies and steady closes above the midpoint of the range.",
        "Short-term pullbacks are being absorbed near the reclaimed value area rather than accelerating lower.",
        "Relative strength versus major FX pairs improved during the same observation window."
      ],
      riskPlan:
        "Size risk against the 2354.80 invalidation and pay yourself in stages across the three target bands to reduce exposure into extension.",
      invalidation:
        "A decisive move back below the reclaimed support shelf cancels the continuation thesis and shifts the setup back to wait mode.",
      executionNotes: [
        "Let the trade breathe above entry instead of chasing after the first impulse candle.",
        "Reduce exposure once TP1 prints and trail the remainder under new structure if momentum stays healthy."
      ]
    },
    indicators: xauIndicators,
    aiProvider: "groq",
    aiModel: "llama-3.3-70b-versatile",
    outcome: "open",
    realizedR: null,
    closedAt: null
  },
  {
    id: "sig-eurusd-1",
    pairId: 2,
    analysisRunId: "run-2026-05-08-1",
    symbol: "EURUSD",
    displayName: "Euro / US Dollar",
    direction: "sell",
    tradeStyle: "scalp",
    status: "active",
    confidence: 0.76,
    entryPrice: 1.08342,
    stopLoss: 1.0871,
    stopDistancePercent: distance(1.08342, 1.0871),
    targets: ladder(1.08342, { TP1: 1.0808, TP2: 1.0784, TP3: 1.0759 }),
    timeframe: "1h",
    generatedAt: "2026-05-08T09:50:00.000Z",
    expiresAt: "2026-05-08T15:50:00.000Z",
    riskReward: 2.04,
    rationale:
      "Trend structure remains heavy below the session pivot. A failed retest opens room toward the lower value area if dollar strength persists.",
    reasoning: {
      thesis:
        "The pair remains vulnerable while it trades below the session pivot and keeps printing lower highs into supply.",
      confirmations: [
        "Retests into resistance are failing quickly instead of building acceptance.",
        "The latest lower high aligned with soft euro momentum and steady dollar demand.",
        "Intraday downside targets remain open with no meaningful support reclaimed yet."
      ],
      riskPlan:
        "Keep risk tight above 1.08710 and distribute exits through the target ladder because EURUSD can mean-revert sharply around US data windows.",
      invalidation:
        "Acceptance back above the pivot with higher lows would neutralize the short idea and move the pair back into balance.",
      executionNotes: [
        "Respect the scheduled macro calendar before adding size.",
        "If the first target hits too quickly, bank partials and let the rest trail with structure."
      ]
    },
    indicators: eurIndicators,
    aiProvider: "groq",
    aiModel: "llama-3.3-70b-versatile",
    outcome: "hit_tp1",
    realizedR: 1.2,
    closedAt: "2026-05-08T12:30:00.000Z"
  },
  {
    id: "sig-gbpusd-1",
    pairId: 3,
    analysisRunId: "run-2026-05-08-1",
    symbol: "GBPUSD",
    displayName: "British Pound / US Dollar",
    direction: "neutral",
    tradeStyle: "swing",
    status: "watchlist",
    confidence: 0.61,
    entryPrice: 1.27125,
    stopLoss: null,
    stopDistancePercent: null,
    targets: [],
    timeframe: "4h",
    generatedAt: "2026-05-08T08:15:00.000Z",
    expiresAt: "2026-05-08T20:15:00.000Z",
    riskReward: null,
    rationale:
      "Price is balanced between weekly liquidity zones. Waiting for a clean break protects capital until directional conviction improves.",
    reasoning: {
      thesis:
        "No trade is the trade for now. GBPUSD is rotating in balance and has not earned directional commitment.",
      confirmations: [
        "Both buyers and sellers have defended their zones without follow-through.",
        "Recent candles show overlap rather than trend expansion.",
        "Momentum signals are mixed across the current 4h structure."
      ],
      riskPlan:
        "Stand aside until the range resolves. Preserving capital here is part of the plan, not a missed opportunity.",
      invalidation:
        "A clean break with acceptance outside the current weekly balance would replace the neutral stance with a directional setup.",
      executionNotes: [
        "Set alerts above resistance and below support.",
        "Wait for confirmation before defining stop and target structure."
      ]
    },
    indicators: null,
    aiProvider: "groq",
    aiModel: "llama-3.3-70b-versatile",
    outcome: "open",
    realizedR: null,
    closedAt: null
  },
  {
    id: "sig-usdjpy-1",
    pairId: 4,
    analysisRunId: "run-2026-05-07-2",
    symbol: "USDJPY",
    displayName: "US Dollar / Japanese Yen",
    direction: "buy",
    tradeStyle: "scalp",
    status: "expired",
    confidence: 0.69,
    entryPrice: 155.82,
    stopLoss: 155.32,
    stopDistancePercent: distance(155.82, 155.32),
    targets: ladder(155.82, { TP1: 156.15, TP2: 156.42, TP3: 156.74 }),
    timeframe: "1h",
    generatedAt: "2026-05-07T20:10:00.000Z",
    expiresAt: "2026-05-08T02:10:00.000Z",
    riskReward: 1.84,
    rationale:
      "The setup lost freshness after Asia session range expansion. Keep it archived for model review, not execution.",
    reasoning: {
      thesis:
        "The original continuation thesis worked for a while, but the setup is no longer timely enough for execution.",
      confirmations: [
        "Most of the expansion already happened during the prior session.",
        "Late entries would inherit weaker reward relative to remaining upside.",
        "The pair is more useful now as a model-review example than a fresh trade."
      ],
      riskPlan:
        "Archive the setup and use it for post-trade learning instead of forcing a late execution.",
      invalidation:
        "Not applicable for fresh execution because the signal has expired.",
      executionNotes: [
        "Review how quickly the pair moved after trigger.",
        "Compare the realized path against the original target ladder for model calibration."
      ]
    },
    indicators: null,
    aiProvider: "groq",
    aiModel: "llama-3.3-70b-versatile",
    outcome: "hit_sl",
    realizedR: -1,
    closedAt: "2026-05-08T01:30:00.000Z"
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

export function getTradingPairBySymbol(symbol: string): TradingPair | undefined {
  return tradingPairs.find((pair) => pair.symbol === symbol.toUpperCase());
}

export function getSignalById(signalId: string): Signal | undefined {
  return signals.find((signal) => signal.id === signalId);
}

export function getSignalsForPair(symbol: string): Signal[] {
  return signals.filter((signal) => signal.symbol === symbol.toUpperCase());
}
