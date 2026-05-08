import type { PriceCandle, Signal, SignalStats, TradingPair } from "@/types/signal";

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
    targets: [
      { label: "TP1", price: 2379.6 },
      { label: "TP2", price: 2388.9 },
      { label: "TP3", price: 2396.2 }
    ],
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
    }
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
    targets: [
      { label: "TP1", price: 1.0808 },
      { label: "TP2", price: 1.0784 },
      { label: "TP3", price: 1.0759 }
    ],
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
    }
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
    }
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
    targets: [
      { label: "TP1", price: 156.15 },
      { label: "TP2", price: 156.42 },
      { label: "TP3", price: 156.74 }
    ],
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
    }
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

function generateCandles(
  startTime: string,
  opens: number[],
  closes: number[],
  highs: number[],
  lows: number[],
  volumes: number[],
  stepHours: number
): PriceCandle[] {
  const startMs = new Date(startTime).getTime();

  return opens.map((open, index) => ({
    time: new Date(startMs + index * stepHours * 60 * 60 * 1000).toISOString(),
    open,
    high: highs[index],
    low: lows[index],
    close: closes[index],
    volume: volumes[index]
  }));
}

export const candlesBySymbol: Record<string, PriceCandle[]> = {
  XAUUSD: generateCandles(
    "2026-05-07T11:00:00.000Z",
    [2347.1, 2349.4, 2351.3, 2353.1, 2355.4, 2357.7, 2359.2, 2361.8, 2360.5, 2363.9, 2365.8, 2366.7, 2364.6, 2366.2, 2368.4, 2371.1],
    [2349.4, 2351.3, 2353.1, 2355.4, 2357.7, 2359.2, 2361.8, 2360.5, 2363.9, 2365.8, 2366.7, 2364.6, 2366.2, 2368.4, 2371.1, 2374.2],
    [2350.3, 2352.1, 2354.4, 2356.6, 2358.8, 2360.3, 2362.6, 2363.5, 2364.5, 2366.9, 2367.8, 2368.1, 2367.2, 2369.9, 2372.4, 2376.3],
    [2346.3, 2348.6, 2350.7, 2352.6, 2354.5, 2356.1, 2358.3, 2358.9, 2359.8, 2362.1, 2364.2, 2363.4, 2363.8, 2365.5, 2367.2, 2369.4],
    [820, 860, 910, 960, 1015, 1080, 1140, 1025, 980, 1160, 1240, 990, 1005, 1175, 1310, 1425],
    1
  ),
  EURUSD: generateCandles(
    "2026-05-07T10:00:00.000Z",
    [1.0892, 1.0887, 1.0881, 1.0874, 1.0868, 1.0862, 1.0856, 1.0851, 1.0848, 1.0844, 1.0842, 1.0839, 1.0841, 1.0838, 1.0836, 1.0834],
    [1.0887, 1.0881, 1.0874, 1.0868, 1.0862, 1.0856, 1.0851, 1.0848, 1.0844, 1.0842, 1.0839, 1.0841, 1.0838, 1.0836, 1.0834, 1.0828],
    [1.0896, 1.0891, 1.0885, 1.0879, 1.0873, 1.0867, 1.0861, 1.0854, 1.0850, 1.0848, 1.0846, 1.0845, 1.0844, 1.0840, 1.0838, 1.0836],
    [1.0883, 1.0878, 1.0870, 1.0863, 1.0858, 1.0852, 1.0848, 1.0844, 1.0840, 1.0838, 1.0835, 1.0834, 1.0832, 1.0830, 1.0827, 1.0822],
    [510, 545, 560, 615, 640, 655, 670, 690, 720, 705, 735, 760, 715, 745, 780, 825],
    1
  ),
  GBPUSD: generateCandles(
    "2026-05-06T08:00:00.000Z",
    [1.2682, 1.2691, 1.2704, 1.2698, 1.2710, 1.2722, 1.2714, 1.2708, 1.2719, 1.2721, 1.2713, 1.2709],
    [1.2691, 1.2704, 1.2698, 1.2710, 1.2722, 1.2714, 1.2708, 1.2719, 1.2721, 1.2713, 1.2709, 1.2712],
    [1.2696, 1.2709, 1.2710, 1.2715, 1.2727, 1.2728, 1.2719, 1.2723, 1.2726, 1.2724, 1.2718, 1.2717],
    [1.2679, 1.2688, 1.2693, 1.2694, 1.2703, 1.2709, 1.2702, 1.2701, 1.2712, 1.2707, 1.2702, 1.2705],
    [460, 505, 540, 520, 575, 590, 560, 548, 615, 602, 588, 610],
    4
  ),
  USDJPY: generateCandles(
    "2026-05-07T09:00:00.000Z",
    [155.12, 155.26, 155.41, 155.56, 155.48, 155.64, 155.78, 155.91, 155.84, 155.79],
    [155.26, 155.41, 155.56, 155.48, 155.64, 155.78, 155.91, 155.84, 155.79, 155.62],
    [155.31, 155.47, 155.62, 155.68, 155.73, 155.83, 155.98, 155.96, 155.89, 155.86],
    [155.05, 155.18, 155.33, 155.39, 155.42, 155.58, 155.66, 155.71, 155.63, 155.49],
    [390, 410, 435, 420, 450, 472, 495, 480, 462, 438],
    1
  )
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

export function getCandlesForPair(symbol: string): PriceCandle[] {
  return candlesBySymbol[symbol.toUpperCase()] ?? [];
}
