import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { ApiClientError } from "@/services/api";

type ErrorStateProps = {
  error: Error;
  onRetry?: () => void;
  title?: string;
};

function getMessage(error: Error): string {
  if (error instanceof ApiClientError) {
    return `${error.detail.code}: ${error.detail.message}`;
  }

  return error.message;
}

export function ErrorState({
  error,
  onRetry,
  title = "Something needs attention"
}: ErrorStateProps) {
  return (
    <div className="rounded-lg border border-[#6e2029] bg-[var(--red-soft)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[var(--red-strong)]" />
          <div>
            <h3 className="text-sm font-semibold text-[#fff8df]">{title}</h3>
            <p className="mt-1 text-sm leading-6 text-[#ffc4c7]">{getMessage(error)}</p>
          </div>
        </div>
        {onRetry ? (
          <Button onClick={onRetry} size="sm" variant="secondary">
            Retry
          </Button>
        ) : null}
      </div>
    </div>
  );
}
