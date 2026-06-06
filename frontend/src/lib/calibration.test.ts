import { describe, expect, it } from "vitest";

import { calibrationForConfidence } from "@/lib/calibration";
import type { CalibrationBucket } from "@/types/performance";

function bucket(lower: number, upper: number, count: number, winRate = 0.5): CalibrationBucket {
  return {
    label: `${Math.round(lower * 100)}-${Math.round(upper * 100)}%`,
    lower,
    upper,
    count,
    avgConfidence: (lower + upper) / 2,
    winRate,
    wins: Math.round(count * winRate)
  };
}

const BUCKETS: CalibrationBucket[] = [
  bucket(0, 0.2, 0),
  bucket(0.2, 0.4, 3),
  bucket(0.4, 0.6, 5),
  bucket(0.6, 0.8, 4),
  bucket(0.8, 1, 6, 0.66)
];

describe("calibrationForConfidence", () => {
  it("finds the band a confidence falls into", () => {
    expect(calibrationForConfidence(BUCKETS, 0.85)?.label).toBe("80-100%");
    expect(calibrationForConfidence(BUCKETS, 0.5)?.label).toBe("40-60%");
  });

  it("puts a perfect 1.0 confidence in the closed top band", () => {
    expect(calibrationForConfidence(BUCKETS, 1)?.label).toBe("80-100%");
  });

  it("returns null for a band with no closed history", () => {
    expect(calibrationForConfidence(BUCKETS, 0.1)).toBeNull();
  });

  it("returns null when there are no buckets", () => {
    expect(calibrationForConfidence([], 0.7)).toBeNull();
  });
});
