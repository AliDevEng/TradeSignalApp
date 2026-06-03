import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ExpiryBadge } from "@/components/signals/ExpiryBadge";

describe("ExpiryBadge", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-02T12:00:00.000Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders an open-ended badge when there is no expiry", () => {
    render(<ExpiryBadge expiresAt={null} />);
    expect(screen.getByText("Open-ended")).toBeInTheDocument();
  });

  it("shows a stable placeholder before the clock mounts", () => {
    render(<ExpiryBadge expiresAt="2026-06-02T13:00:00.000Z" />);
    expect(screen.getByText("Expiry tracked")).toBeInTheDocument();
  });

  it("counts down while the signal is still valid", () => {
    render(<ExpiryBadge expiresAt="2026-06-02T14:00:00.000Z" />);
    act(() => {
      vi.advanceTimersByTime(10);
    });
    expect(screen.getByText(/Expires/)).toBeInTheDocument();
  });

  it("flips to an expired state once the expiry has passed", () => {
    render(<ExpiryBadge expiresAt="2026-06-02T11:00:00.000Z" />);
    act(() => {
      vi.advanceTimersByTime(10);
    });
    expect(screen.getByText(/Expired/)).toBeInTheDocument();
  });
});
