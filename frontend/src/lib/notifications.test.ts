import { describe, expect, it } from "vitest";

import { describeNotificationStatus } from "@/lib/notifications";

describe("describeNotificationStatus", () => {
  it("reports a running dispatcher as connected", () => {
    const view = describeNotificationStatus({ status: "ok" });
    expect(view.tone).toBe("connected");
    expect(view.label).toBe("Connected");
  });

  it("reports a config-disabled subsystem as a benign disabled state", () => {
    const view = describeNotificationStatus({ status: "not_configured" });
    expect(view.tone).toBe("disabled");
    expect(view.label).toBe("Not configured");
  });

  it("reports an enabled-but-stopped dispatcher as down", () => {
    const view = describeNotificationStatus({ status: "down" });
    expect(view.tone).toBe("down");
    expect(view.label).toBe("Down");
  });

  it("falls back to unknown when the component is absent", () => {
    const view = describeNotificationStatus(undefined);
    expect(view.tone).toBe("unknown");
    expect(view.label).toBe("Unknown");
  });
});
