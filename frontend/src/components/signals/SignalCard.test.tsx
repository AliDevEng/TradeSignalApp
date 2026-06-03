import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SignalCard } from "@/components/signals/SignalCard";
import { buildSignal } from "@/test/fixtures";

describe("SignalCard", () => {
  it("renders the symbol, confidence and entry price", () => {
    render(<SignalCard density="comfortable" signal={buildSignal()} />);

    expect(screen.getByRole("heading", { name: "XAUUSD" })).toBeInTheDocument();
    expect(screen.getByText("84%")).toBeInTheDocument();
    expect(screen.getByText("2,368.42")).toBeInTheDocument();
  });

  it("links to the signal and pair detail routes", () => {
    render(<SignalCard density="comfortable" signal={buildSignal()} />);

    expect(screen.getByRole("link", { name: /review signal/i })).toHaveAttribute(
      "href",
      "/signals/sig-xauusd-1"
    );
    expect(screen.getByRole("link", { name: /pair view/i })).toHaveAttribute(
      "href",
      "/pairs/XAUUSD"
    );
  });

  it("hides the rationale in compact density", () => {
    const rationale = "Bullish continuation above the reclaimed shelf.";
    const { rerender } = render(<SignalCard density="comfortable" signal={buildSignal()} />);
    expect(screen.getByText(rationale)).toBeInTheDocument();

    rerender(<SignalCard density="compact" signal={buildSignal()} />);
    expect(screen.queryByText(rationale)).not.toBeInTheDocument();
  });

  it("shows Hold for risk/reward when none is computed", () => {
    render(<SignalCard density="comfortable" signal={buildSignal({ riskReward: null })} />);
    expect(screen.getByText("Hold")).toBeInTheDocument();
  });
});
