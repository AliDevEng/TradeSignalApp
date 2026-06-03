import type { Metadata } from "next";

import { DashboardShell } from "@/components/dashboard/DashboardShell";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Live signal feed, portfolio pulse, and API health in one command center."
};

export default function DashboardPage() {
  return <DashboardShell />;
}
