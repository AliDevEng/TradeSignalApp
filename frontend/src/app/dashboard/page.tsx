import type { Metadata } from "next";

import { DashboardShell } from "@/components/dashboard/DashboardShell";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Top setup, live position sizing, risk, and the full signal queue in one command center."
};

export default function DashboardPage() {
  return <DashboardShell />;
}
