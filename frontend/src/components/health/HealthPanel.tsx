"use client";

import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useHealthQuery } from "@/hooks/useHealthQuery";
import { ApiClientError } from "@/services/api";
import type { ComponentState } from "@/types/health";

type HealthPanelProps = {
  compact?: boolean;
};

const statusStyles: Record<ComponentState, string> = {
  ok: "bg-[var(--blue-soft)] text-[var(--blue-strong)] border-[#234f86]",
  degraded: "bg-[var(--gold-soft)] text-[var(--gold-strong)] border-[#6f5620]",
  down: "bg-[var(--red-soft)] text-[var(--red-strong)] border-[#6e2029]",
  not_configured: "bg-[#141b27] text-[#cbd5e1] border-[#344053]"
};

function formatError(error: Error): string {
  if (error instanceof ApiClientError) {
    return error.detail.message;
  }

  return error.message;
}

export function HealthPanel({ compact = false }: HealthPanelProps) {
  const { data, error, isLoading, isFetching } = useHealthQuery();

  if (isLoading) {
    return (
      <div className="rounded-lg border border-[var(--panel-border)] bg-[#0d131c] p-5">
        <LoadingSpinner label="Checking backend status" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-[#6e2029] bg-[var(--red-soft)] p-5 text-sm text-[var(--red-strong)]">
        {formatError(error)}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-lg border border-[var(--panel-border)] bg-[#0d131c] p-5 text-sm text-[var(--muted)]">
        No health data returned.
      </div>
    );
  }

  return (
    <div className={compact ? "space-y-3" : "space-y-4"}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-[var(--muted)]">Overall status</p>
          <p
            className={
              compact
                ? "mt-1 text-xl font-semibold capitalize text-[#fff8df]"
                : "mt-1 text-2xl font-semibold capitalize text-[#fff8df]"
            }
          >
            {data.status}
          </p>
        </div>
        <Badge className={statusStyles[data.status]}>
          {isFetching ? "Refreshing" : data.environment}
        </Badge>
      </div>

      <div className={compact ? "grid gap-2" : "grid gap-3 sm:grid-cols-2"}>
        {Object.entries(data.components).map(([name, component]) => (
          <div className="rounded-lg border border-[var(--panel-border)] bg-[#0d131c] p-4" key={name}>
            <div className="flex items-center justify-between gap-3">
              <p className="font-medium capitalize text-[#fff8df]">{name.replaceAll("_", " ")}</p>
              <Badge className={`max-w-[132px] justify-center text-center ${statusStyles[component.status]}`}>
                {component.status.replaceAll("_", " ")}
              </Badge>
            </div>
            {component.detail ? (
              <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{component.detail}</p>
            ) : null}
          </div>
        ))}
      </div>

      <p className="text-xs leading-5 text-[var(--muted)]">
        API {data.version} | Python {data.python_version} |{" "}
        {new Intl.DateTimeFormat("en", {
          dateStyle: "medium",
          timeStyle: "short"
        }).format(new Date(data.timestamp))}
      </p>
    </div>
  );
}
