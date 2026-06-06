/**
 * Pure presentation mapping for the backend `notifications` health component.
 * Kept free of React so the status→label/tone logic is unit-tested directly; the
 * Telegram connect panel renders the result.
 */

import type { ComponentState, ComponentStatus } from "@/types/health";

export type NotificationConnectionTone = "connected" | "disabled" | "down" | "unknown";

export type NotificationConnectionView = {
  tone: NotificationConnectionTone;
  label: string;
  hint: string;
};

const VIEWS: Record<ComponentState, NotificationConnectionView> = {
  ok: {
    tone: "connected",
    label: "Connected",
    hint: "The backend dispatcher is running and delivering signals to Telegram."
  },
  not_configured: {
    tone: "disabled",
    label: "Not configured",
    hint: "Off-platform delivery is disabled. Set the backend env vars below to enable it."
  },
  down: {
    tone: "down",
    label: "Down",
    hint: "Notifications are enabled but the dispatcher is not running — check the backend logs."
  },
  degraded: {
    tone: "down",
    label: "Degraded",
    hint: "The notification subsystem reported a problem — check the backend logs."
  }
};

const UNKNOWN: NotificationConnectionView = {
  tone: "unknown",
  label: "Unknown",
  hint: "Could not read the backend health status."
};

/** Map the `notifications` health component onto a connection view. */
export function describeNotificationStatus(
  component: ComponentStatus | undefined
): NotificationConnectionView {
  if (!component) {
    return UNKNOWN;
  }
  return VIEWS[component.status] ?? UNKNOWN;
}
