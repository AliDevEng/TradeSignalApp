import { describe, expect, it } from "vitest";

import { mapApiPair, mapApiSignal } from "@/lib/signalMappers";
import type { ApiPair, ApiSignal } from "@/types/tradeApi";
import type { TradingPair } from "@/types/signal";

const pair: TradingPair = {
  id: 1,
  symbol: "XAUUSD",
  baseCurrency: "XAU",
  quoteCurrency: "USD",
  displayName: "Gold / US Dollar",
  isActive: true
};

function buildApiSignal(overrides: Partial<ApiSignal> = {}): ApiSignal {
  return {
    id: "sig-1",
    pair_id: 1,
    pair_symbol: "XAUUSD",
    analysis_run_id: "run-1",
    direction: "buy",
    signal_type: "swing",
    confidence: 0.84,
    entry_price: "2368.42",
    stop_loss: "2354.80",
    take_profit: "2379.60",
    take_profit_2: "2388.90",
    take_profit_3: "2396.20",
    timeframe: "1h",
    rationale: "Continuation setup.",
    indicators_snapshot: {
      as_of: "2026-05-08T10:00:00.000Z",
      candles_analyzed: 200,
      last_close: 2367.9,
      rsi_14: 63.4,
      macd: 4.21,
      macd_signal: 3.08,
      macd_histogram: 1.13,
      ema_20: 2362.7,
      ema_200: 2338.5,
      bb_upper: 2374.2,
      bb_lower: 2348.6
    },
    generated_at: "2026-05-08T10:35:00.000Z",
    expires_at: "2100-01-01T00:00:00.000Z",
    ai_provider: "groq",
    ai_model: "llama-3.3-70b-versatile",
    outcome: "open",
    realized_r: null,
    closed_at: null,
    ...overrides
  };
}

describe("mapApiPair", () => {
  it("derives a display name when the API omits one", () => {
    const apiPair: ApiPair = {
      id: 2,
      symbol: "EURUSD",
      base_currency: "EUR",
      quote_currency: "USD",
      display_name: null,
      is_active: true
    };

    expect(mapApiPair(apiPair).displayName).toBe("EUR / USD");
  });
});

describe("mapApiSignal", () => {
  it("builds the full TP1..TP3 ladder with entry-relative distances", () => {
    const signal = mapApiSignal(buildApiSignal(), [pair]);

    expect(signal.targets.map((target) => target.label)).toEqual(["TP1", "TP2", "TP3"]);
    expect(signal.targets[0]?.price).toBe(2379.6);
    // (2379.6 - 2368.42) / 2368.42 ≈ 0.00472
    expect(signal.targets[0]?.distancePercent).toBeCloseTo(0.00472, 4);
  });

  it("computes stop distance and risk/reward", () => {
    const signal = mapApiSignal(buildApiSignal(), [pair]);

    expect(signal.stopDistancePercent).toBeCloseTo(-0.00575, 4);
    // reward 11.18 / risk 13.62 ≈ 0.82
    expect(signal.riskReward).toBeCloseTo(0.82, 2);
  });

  it("normalises the indicator snapshot to camelCase", () => {
    const signal = mapApiSignal(buildApiSignal(), [pair]);

    expect(signal.indicators?.rsi14).toBe(63.4);
    expect(signal.indicators?.ema200).toBe(2338.5);
    expect(signal.indicators?.macdHistogram).toBe(1.13);
  });

  it("omits ladder entries for missing take-profits", () => {
    const signal = mapApiSignal(
      buildApiSignal({ take_profit_2: null, take_profit_3: null }),
      [pair]
    );

    expect(signal.targets).toHaveLength(1);
  });

  it("marks a signal expired once its expiry has passed", () => {
    const signal = mapApiSignal(
      buildApiSignal({ expires_at: "2000-01-01T00:00:00.000Z" }),
      [pair]
    );

    expect(signal.status).toBe("expired");
  });

  it("resolves the symbol from the pair list when pair_symbol is null", () => {
    const signal = mapApiSignal(buildApiSignal({ pair_symbol: null }), [pair]);

    expect(signal.symbol).toBe("XAUUSD");
    expect(signal.displayName).toBe("Gold / US Dollar");
  });

  it("carries AI provider/model through", () => {
    const signal = mapApiSignal(buildApiSignal(), [pair]);

    expect(signal.aiProvider).toBe("groq");
    expect(signal.aiModel).toBe("llama-3.3-70b-versatile");
  });

  it("maps the trade style through", () => {
    expect(mapApiSignal(buildApiSignal({ signal_type: "scalp" }), [pair]).tradeStyle).toBe("scalp");
    expect(mapApiSignal(buildApiSignal({ signal_type: "swing" }), [pair]).tradeStyle).toBe("swing");
  });

  it("defaults the outcome to open and leaves R/closedAt empty when unset", () => {
    const signal = mapApiSignal(buildApiSignal(), [pair]);

    expect(signal.outcome).toBe("open");
    expect(signal.realizedR).toBeNull();
    expect(signal.closedAt).toBeNull();
  });

  it("maps a closed outcome with its realised R (Decimal string) and close time", () => {
    const signal = mapApiSignal(
      buildApiSignal({
        outcome: "hit_tp2",
        realized_r: "2.1000",
        closed_at: "2026-05-08T12:00:00.000Z"
      }),
      [pair]
    );

    expect(signal.outcome).toBe("hit_tp2");
    expect(signal.realizedR).toBe(2.1);
    expect(signal.closedAt).toBe("2026-05-08T12:00:00.000Z");
  });

  it("falls back to open for an unrecognised outcome value", () => {
    const signal = mapApiSignal(
      buildApiSignal({ outcome: "moon" as unknown as ApiSignal["outcome"] }),
      [pair]
    );

    expect(signal.outcome).toBe("open");
  });
});
