import { describe, expect, it } from "vitest";

import { formatRunDuration, runStatusTone } from "@/lib/analysisRun";

describe("runStatusTone", () => {
  it("maps statuses to badge tones", () => {
    expect(runStatusTone.success).toBe("success");
    expect(runStatusTone.failed).toBe("danger");
    expect(runStatusTone.running).toBe("info");
  });
});

describe("formatRunDuration", () => {
  it("returns null while a run is in progress", () => {
    expect(formatRunDuration("2026-06-02T12:00:00Z", null)).toBeNull();
  });

  it("formats sub-second durations in milliseconds", () => {
    expect(formatRunDuration("2026-06-02T12:00:00.000Z", "2026-06-02T12:00:00.400Z")).toBe("400 ms");
  });

  it("formats seconds with one decimal", () => {
    expect(formatRunDuration("2026-06-02T12:00:00.000Z", "2026-06-02T12:00:04.500Z")).toBe("4.5 s");
  });

  it("formats minutes and seconds", () => {
    expect(formatRunDuration("2026-06-02T12:00:00.000Z", "2026-06-02T12:02:05.000Z")).toBe("2m 5s");
  });

  it("returns null for an inverted interval", () => {
    expect(formatRunDuration("2026-06-02T12:00:05Z", "2026-06-02T12:00:00Z")).toBeNull();
  });
});
