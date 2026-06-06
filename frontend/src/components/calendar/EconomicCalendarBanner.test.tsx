import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const NOW = new Date("2026-06-07T10:00:00Z").getTime();

// Pin the clock so the countdown is deterministic.
vi.mock("@/hooks/useNow", () => ({ useNow: () => NOW }));

// Provide a fixed upcoming high-impact event (the factory is hoisted, so build
// the data inline rather than referencing an outer const).
vi.mock("@/hooks/useCalendar", () => ({
  useCalendar: () => ({
    events: [
      {
        title: "US CPI (YoY)",
        currency: "USD",
        impact: "high",
        scheduledAt: new Date(new Date("2026-06-07T10:00:00Z").getTime() + 2 * 3_600_000).toISOString()
      }
    ],
    isLoading: false
  })
}));

import { EconomicCalendarBanner } from "@/components/calendar/EconomicCalendarBanner";
import { useCalendarDismissStore } from "@/store/calendarDismissStore";

describe("EconomicCalendarBanner", () => {
  beforeEach(() => {
    useCalendarDismissStore.setState({ dismissed: [] });
    localStorage.clear();
  });

  it("warns about the next imminent high-impact event", () => {
    render(<EconomicCalendarBanner />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/high-impact USD event/i)).toBeInTheDocument();
    expect(screen.getByText(/US CPI \(YoY\)/)).toBeInTheDocument();
  });

  it("dismisses the banner and remembers it", () => {
    render(<EconomicCalendarBanner />);

    fireEvent.click(screen.getByRole("button", { name: /dismiss event warning/i }));

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(useCalendarDismissStore.getState().dismissed).toHaveLength(1);
  });
});
