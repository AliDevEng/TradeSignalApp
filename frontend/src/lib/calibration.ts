import type { CalibrationBucket } from "@/types/performance";

/**
 * The confidence-calibration bucket a stated confidence falls into, or `null`
 * when there is no usable history. Pure, so the band-matching is unit-tested
 * directly; the card hint renders the result.
 *
 * Bands are `[lower, upper)` with the top band closed at 1.0 (a 100% stated
 * confidence belongs in the 80-100% band). A bucket with no closed signals
 * (`count === 0`) returns `null` — without history there's nothing honest to say
 * about whether the AI's confidence holds up.
 */
export function calibrationForConfidence(
  buckets: CalibrationBucket[],
  confidence: number
): CalibrationBucket | null {
  const c = Math.min(Math.max(confidence, 0), 1);
  const bucket =
    buckets.find((b) => c >= b.lower && (c < b.upper || b.upper >= 1)) ?? null;
  return bucket && bucket.count > 0 ? bucket : null;
}
