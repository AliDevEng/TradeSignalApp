import type { Metadata } from "next";

import { AnalysisRunsPage } from "@/components/analysis/AnalysisRunsPage";

export const metadata: Metadata = {
  title: "Analysis Runs",
  description: "Scheduler and manual pipeline runs with provider metadata and pair-level outcomes."
};

export default function AnalysisPage() {
  return <AnalysisRunsPage />;
}
