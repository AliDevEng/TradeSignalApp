import { describe, expect, it } from "vitest";

import { mapApiPositionSize } from "@/lib/riskMappers";
import type { ApiPositionSize } from "@/types/tradeApi";

const API: ApiPositionSize = {
  pair: "XAUUSD",
  quote_currency: "USD",
  contract_size: "100",
  min_lot: "0.01",
  lot_step: "0.01",
  requested_risk_amount: "100.00",
  stop_distance: "10",
  lots: "0.10",
  units: "10.00",
  risk_amount: "100.00",
  position_value: "20000.00",
  pip_value: "0.10",
  take_profits: [
    { price: "2020", distance: "20", risk_reward: "2.00", profit_amount: "200.00" },
    { price: "2015", distance: "15", risk_reward: "1.50", profit_amount: "150.00" }
  ]
};

describe("mapApiPositionSize", () => {
  it("parses Decimal-string fields to numbers", () => {
    const result = mapApiPositionSize(API);

    expect(result.pair).toBe("XAUUSD");
    expect(result.quoteCurrency).toBe("USD");
    expect(result.lots).toBe(0.1);
    expect(result.riskAmount).toBe(100);
    expect(result.positionValue).toBe(20000);
    expect(result.pipValue).toBe(0.1);
  });

  it("maps each take-profit projection", () => {
    const result = mapApiPositionSize(API);

    expect(result.takeProfits).toHaveLength(2);
    expect(result.takeProfits[0]).toEqual({
      price: 2020,
      distance: 20,
      riskReward: 2,
      profitAmount: 200
    });
    expect(result.takeProfits[1].riskReward).toBe(1.5);
  });

  it("coerces a malformed numeric field to 0 rather than NaN", () => {
    const result = mapApiPositionSize({ ...API, lots: "not-a-number" });
    expect(result.lots).toBe(0);
  });
});
