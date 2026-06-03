import type { Metadata } from "next";

import { SignalsBrowsePage } from "@/components/signals/SignalsBrowsePage";

export const metadata: Metadata = {
  title: "Signals",
  description: "Browse all generated trade setups with shareable filters and server-side pagination."
};

export default function SignalsPage() {
  return <SignalsBrowsePage />;
}
