/**
 * UI-facing economic-calendar types — the parsed mirror of the backend
 * `/calendar` payload (Iteration 10). High-impact macro events (CPI, FOMC, NFP)
 * are the news that moves Gold; the dashboard surfaces them as a banner + a
 * per-day strip so a trader isn't blindsided trading into a release.
 */

export type EconomicEventImpact = "high" | "medium" | "low" | string;

export type EconomicEvent = {
  title: string;
  /** The currency the release affects, e.g. "USD". */
  currency: string;
  impact: EconomicEventImpact;
  /** ISO 8601 scheduled time. */
  scheduledAt: string;
};

export type EconomicCalendar = {
  /** Mirrors `ECONOMIC_CALENDAR_ENABLED` — distinguishes "off" from "nothing scheduled". */
  enabled: boolean;
  withinHours: number;
  events: EconomicEvent[];
};
