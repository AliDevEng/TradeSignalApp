import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { IndicatorsPanel } from "@/components/signals/IndicatorsPanel";
import { sampleIndicators } from "@/test/fixtures";

describe("IndicatorsPanel", () => {
  it("renders an empty state when there is no snapshot", () => {
    render(<IndicatorsPanel indicators={null} />);
    expect(screen.getByText("No indicator data")).toBeInTheDocument();
  });

  it("renders grouped indicator rows from a snapshot", () => {
    render(<IndicatorsPanel indicators={sampleIndicators} />);

    expect(screen.getByRole("heading", { name: "Indicator Snapshot" })).toBeInTheDocument();
    expect(screen.getByText("Momentum")).toBeInTheDocument();
    expect(screen.getByText("Trend")).toBeInTheDocument();
    expect(screen.getByText("Volatility")).toBeInTheDocument();
    expect(screen.getByText("RSI (14)")).toBeInTheDocument();
    expect(screen.getByText("63.400")).toBeInTheDocument();
  });
});
