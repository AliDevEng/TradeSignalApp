import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PositionSizeReadout } from "@/components/risk/PositionSizeReadout";
import type { PositionSize } from "@/types/risk";

function makeResult(overrides: Partial<PositionSize> = {}): PositionSize {
  return {
    pair: "XAUUSD",
    quoteCurrency: "USD",
    contractSize: 100,
    minLot: 0.01,
    lotStep: 0.01,
    requestedRiskAmount: 100,
    stopDistance: 10,
    lots: 0.1,
    units: 10,
    riskAmount: 100,
    positionValue: 20000,
    pipValue: 0.1,
    takeProfits: [
      { price: 2020, distance: 20, riskReward: 2, profitAmount: 200 },
      { price: 2015, distance: 15, riskReward: 1.5, profitAmount: 150 }
    ],
    ...overrides
  };
}

describe("PositionSizeReadout", () => {
  it("renders lots, risk, and the reward per take-profit", () => {
    render(<PositionSizeReadout result={makeResult()} />);

    expect(screen.getByText("Lots")).toBeInTheDocument();
    expect(screen.getByText("0.10")).toBeInTheDocument();
    // Risk amount as currency.
    expect(screen.getByText("$100.00")).toBeInTheDocument();
    // Per-TP rows: R:R and profit.
    expect(screen.getByText("TP1")).toBeInTheDocument();
    expect(screen.getByText("2 : 1")).toBeInTheDocument();
    expect(screen.getByText("+$200.00")).toBeInTheDocument();
    expect(screen.getByText("1.5 : 1")).toBeInTheDocument();
  });

  it("explains when the trade is not affordable (zero lots)", () => {
    render(<PositionSizeReadout result={makeResult({ lots: 0, units: 0, riskAmount: 0 })} />);

    expect(screen.getByText(/too/i)).toBeInTheDocument();
    // The reward rows are not rendered for an unsized position.
    expect(screen.queryByText("TP1")).not.toBeInTheDocument();
  });
});
