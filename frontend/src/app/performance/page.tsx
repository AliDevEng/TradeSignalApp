import type { Metadata } from "next";

import { PerformanceDashboardPage } from "@/components/performance/PerformanceDashboardPage";

export const metadata: Metadata = {
  title: "Performance",
  description:
    "The track record scoreboard: win-rate, profit factor, expectancy and total R, an equity curve of cumulative R, and an AI confidence-calibration read across every closed signal."
};

export default function PerformancePage() {
  return <PerformanceDashboardPage />;
}
