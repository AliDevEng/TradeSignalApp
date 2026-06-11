import { describe, expect, it } from "vitest";

import { phaseStatuses, pipelineProgressPercent } from "@/lib/pipeline";
import type { PipelineProgress } from "@/types/stream";

function progress(overrides: Partial<PipelineProgress> = {}): PipelineProgress {
  return {
    runId: "run-1",
    phase: "fetching",
    message: "",
    pair: "XAUUSD",
    pairsTotal: 1,
    pairsCompleted: 0,
    step: null,
    stepsTotal: null,
    updatedAt: 0,
    ...overrides
  };
}

describe("phaseStatuses", () => {
  it("marks earlier phases done, the current active, later pending", () => {
    const statuses = phaseStatuses(progress({ phase: "scoring" }));
    expect(statuses.map((s) => s.status)).toEqual(["done", "done", "active", "pending"]);
  });

  it("sits at the first step when the run is live but not yet phased", () => {
    const statuses = phaseStatuses(progress({ phase: null }));
    expect(statuses[0].status).toBe("active");
  });
});

describe("pipelineProgressPercent", () => {
  it("advances monotonically across phases for a single pair", () => {
    const fetching = pipelineProgressPercent(progress({ phase: "fetching" }));
    const analyzing = pipelineProgressPercent(progress({ phase: "analyzing" }));
    const scoring = pipelineProgressPercent(progress({ phase: "scoring" }));
    expect(fetching).toBeLessThan(analyzing);
    expect(analyzing).toBeLessThan(scoring);
    expect(scoring).toBeLessThanOrEqual(100);
  });

  it("refines the fetching phase by the timeframe step", () => {
    const early = pipelineProgressPercent(progress({ phase: "fetching", step: 1, stepsTotal: 6 }));
    const late = pipelineProgressPercent(progress({ phase: "fetching", step: 5, stepsTotal: 6 }));
    expect(late).toBeGreaterThan(early);
  });

  it("reflects completed pairs in a multi-pair run", () => {
    const firstPair = pipelineProgressPercent(
      progress({ phase: "analyzing", pairsTotal: 2, pairsCompleted: 0 })
    );
    const secondPair = pipelineProgressPercent(
      progress({ phase: "analyzing", pairsTotal: 2, pairsCompleted: 1 })
    );
    expect(secondPair).toBeGreaterThan(firstPair);
  });

  it("clamps to the 0–100 range", () => {
    const percent = pipelineProgressPercent(
      progress({ phase: "persisting", pairsTotal: 1, pairsCompleted: 1 })
    );
    expect(percent).toBeGreaterThanOrEqual(0);
    expect(percent).toBeLessThanOrEqual(100);
  });
});
