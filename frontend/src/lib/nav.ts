/**
 * Shared navigation config + the active-route predicate, so the desktop top bar
 * ({@link AppShell}) and the mobile drawer ({@link MobileNav}) render the exact
 * same destinations and highlight the same active route — one source of truth.
 */

import {
  Activity,
  BarChart3,
  CircleCheckBig,
  Gauge,
  LineChart,
  ServerCog,
  Settings,
  type LucideIcon
} from "lucide-react";

export type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  /** One-line context shown in the mobile drawer (not the dense desktop bar). */
  description: string;
};

/** Primary destinations — the decision surfaces, shown in the desktop top bar. */
export const primaryNav: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: Gauge, description: "Decision overview" },
  { label: "Signals", href: "/signals", icon: Activity, description: "All trade setups" },
  { label: "Analysis", href: "/analysis", icon: BarChart3, description: "Pipeline run ledger" },
  { label: "Closed", href: "/closed", icon: CircleCheckBig, description: "Track-record history" },
  { label: "Performance", href: "/performance", icon: LineChart, description: "Win-rate & equity" }
];

/** Utility destinations — reached via header icons on desktop, the drawer on mobile. */
export const utilityNav: NavItem[] = [
  { label: "System", href: "/system", icon: ServerCog, description: "Backend & stream health" },
  { label: "Settings", href: "/settings", icon: Settings, description: "Alerts, risk & account" }
];

/**
 * Whether `href` is the active route for `pathname`. `/dashboard` doubles as the
 * `/` home; every other route also matches its sub-paths (e.g. `/signals/abc`).
 */
export function isActiveRoute(pathname: string, href: string): boolean {
  const route = href.split("?")[0];

  if (route === "/dashboard") {
    return pathname === "/" || pathname === "/dashboard";
  }

  return pathname === route || pathname.startsWith(`${route}/`);
}
