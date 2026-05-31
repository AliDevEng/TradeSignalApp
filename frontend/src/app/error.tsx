"use client";

import { ErrorState } from "@/components/ui/ErrorState";

type GlobalErrorProps = {
  error: Error;
  reset: () => void;
};

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  return <ErrorState error={error} onRetry={reset} title="This route could not render" />;
}
