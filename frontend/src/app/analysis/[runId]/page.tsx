import type { Metadata } from "next";

import { AnalysisRunDetailPage } from "@/components/analysis/AnalysisRunDetailPage";

type AnalysisRunPageProps = {
  params: Promise<{
    runId: string;
  }>;
};

export const metadata: Metadata = {
  title: "Analysis run",
  description: "Run status, provider metadata, duration, and the signals produced by this pipeline run."
};

export default async function AnalysisRunPage({ params }: AnalysisRunPageProps) {
  const { runId } = await params;

  return <AnalysisRunDetailPage runId={runId} />;
}
