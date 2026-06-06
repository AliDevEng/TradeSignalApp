"use client";

import { Scale } from "lucide-react";

import { usePerformanceQuery } from "@/hooks/useTradeQueries";
import { calibrationForConfidence } from "@/lib/calibration";

/**
 * A small "is the AI calibrated?" hint for a signal's stated confidence: it looks
 * up the realised hit-rate of the confidence band this signal sits in (from the
 * aggregated `/performance` calibration) and shows raw vs realised. Renders
 * nothing until there's history for the band — no honest comparison exists yet.
 *
 * All cards share the one cached performance query, so this adds no per-card
 * network cost.
 */
export function ConfidenceCalibrationHint({ confidence }: { confidence: number }) {
  const query = usePerformanceQuery();
  const bucket = query.data ? calibrationForConfidence(query.data.calibration, confidence) : null;

  if (!bucket) {
    return null;
  }

  const realised = Math.round(bucket.winRate * 100);
  const stated = Math.round(confidence * 100);

  return (
    <p
      className="mt-2 flex items-center gap-1.5 text-[11px] text-[var(--muted)]"
      title={`Stated ${stated}% confidence. Closed signals in the ${bucket.label} band have hit ${realised}% of the time (${bucket.count} closed).`}
    >
      <Scale aria-hidden className="h-3.5 w-3.5 text-[var(--blue-strong)]" />
      <span>
        Calibration: {bucket.label} band has hit{" "}
        <span className="font-semibold text-[#cdd6e3]">{realised}%</span> over {bucket.count} closed
      </span>
    </p>
  );
}
