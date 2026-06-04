import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CalibrationChart } from "@/components/charts/CalibrationChart";
import type { CalibrationBucket } from "@/types/performance";

function bucket(overrides: Partial<CalibrationBucket> = {}): CalibrationBucket {
  return {
    label: "60-80%",
    lower: 0.6,
    upper: 0.8,
    count: 0,
    avgConfidence: 0,
    winRate: 0,
    wins: 0,
    ...overrides
  };
}

const emptyBuckets: CalibrationBucket[] = [
  bucket({ label: "0-20%", lower: 0, upper: 0.2 }),
  bucket({ label: "20-40%", lower: 0.2, upper: 0.4 }),
  bucket({ label: "40-60%", lower: 0.4, upper: 0.6 }),
  bucket({ label: "60-80%", lower: 0.6, upper: 0.8 }),
  bucket({ label: "80-100%", lower: 0.8, upper: 1 })
];

describe("CalibrationChart", () => {
  it("shows an empty state when no band has data", () => {
    render(<CalibrationChart buckets={emptyBuckets} />);

    expect(screen.getByText(/not enough closed trades/i)).toBeInTheDocument();
  });

  it("renders bands and counts once there is data", () => {
    const buckets = [...emptyBuckets];
    buckets[3] = bucket({ count: 4, avgConfidence: 0.7, winRate: 0.5, wins: 2 });

    render(<CalibrationChart buckets={buckets} />);

    expect(screen.getByText("60-80%")).toBeInTheDocument();
    expect(screen.getByText("n=4")).toBeInTheDocument();
    // Predicted + realised legend swatches.
    expect(screen.getByText(/predicted/i)).toBeInTheDocument();
    expect(screen.getByText(/realised/i)).toBeInTheDocument();
  });
});
