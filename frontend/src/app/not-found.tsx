import Link from "next/link";

import { EmptyState } from "@/components/ui/EmptyState";

export default function NotFound() {
  return (
    <EmptyState
      action={
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-[#8f6a20] bg-[var(--gold)] px-4 text-sm font-semibold text-[#0a0c10] transition-colors hover:bg-[var(--gold-strong)]"
          href="/dashboard"
        >
          Back to dashboard
        </Link>
      }
      description="The route or market object you opened does not exist in the current workspace."
      title="Page not found"
    />
  );
}
