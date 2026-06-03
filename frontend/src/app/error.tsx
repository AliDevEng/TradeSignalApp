"use client";

import { useEffect } from "react";

import { ErrorState } from "@/components/ui/ErrorState";
import { reportError } from "@/lib/monitoring";

type RouteErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function RouteError({ error, reset }: RouteErrorProps) {
  useEffect(() => {
    reportError(error, { source: "route-error-boundary", digest: error.digest });
  }, [error]);

  return <ErrorState error={error} onRetry={reset} title="This route could not render" />;
}
