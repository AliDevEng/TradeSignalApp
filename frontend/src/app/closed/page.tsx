import type { Metadata } from "next";

import { ClosedSignalsPage } from "@/components/signals/ClosedSignalsPage";

export const metadata: Metadata = {
  title: "Closed Signals",
  description:
    "The track record: every signal whose price has resolved to a take-profit, stop, or expiry, with its realised R."
};

export default function ClosedPage() {
  return <ClosedSignalsPage />;
}
