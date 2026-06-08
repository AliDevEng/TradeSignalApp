import type { Metadata } from "next";

import { SystemPage } from "@/components/system/SystemPage";

export const metadata: Metadata = {
  title: "System",
  description: "Backend health, the live analysis pipeline, and data-provider status."
};

export default function System() {
  return <SystemPage />;
}
