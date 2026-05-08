"use client";

import { useHealthQuery } from "@/hooks/useHealthQuery";
import { ApiClientError } from "@/services/api";
import type { ComponentState } from "@/types/health";

const statusStyles: Record<ComponentState, string> = {
  ok: "bg-[#e5f6ef] text-[#116149] border-[#bfe6d6]",
  degraded: "bg-[#fff7ed] text-[#9a3412] border-[#fed7aa]",
  down: "bg-[#fff1f2] text-[#be123c] border-[#fecdd3]",
  not_configured: "bg-[#f3f4f6] text-[#4b5563] border-[#d1d5db]"
};

function formatError(error: Error): string {
  if (error instanceof ApiClientError) {
    return error.detail.message;
  }

  return error.message;
}

export function HealthPanel() {
  const { data, error, isLoading, isFetching } = useHealthQuery();

  if (isLoading) {
    return (
      <div className="rounded-lg border border-[var(--panel-border)] bg-[#fafbf7] p-5 text-sm text-[var(--muted)]">
        Checking backend status...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-[#fecdd3] bg-[#fff1f2] p-5 text-sm text-[#be123c]">
        {formatError(error)}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-lg border border-[var(--panel-border)] bg-[#fafbf7] p-5 text-sm text-[var(--muted)]">
        No health data returned.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-[var(--muted)]">Overall status</p>
          <p className="mt-1 text-2xl font-semibold capitalize">{data.status}</p>
        </div>
        <span
          className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${statusStyles[data.status]}`}
        >
          {isFetching ? "Refreshing" : data.environment}
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {Object.entries(data.components).map(([name, component]) => (
          <div className="rounded-lg border border-[var(--panel-border)] p-4" key={name}>
            <div className="flex items-center justify-between gap-3">
              <p className="font-medium capitalize">{name.replaceAll("_", " ")}</p>
              <span
                className={`rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${statusStyles[component.status]}`}
              >
                {component.status.replaceAll("_", " ")}
              </span>
            </div>
            {component.detail ? (
              <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{component.detail}</p>
            ) : null}
          </div>
        ))}
      </div>

      <p className="text-xs text-[var(--muted)]">
        API {data.version} · Python {data.python_version} ·{" "}
        {new Intl.DateTimeFormat("en", {
          dateStyle: "medium",
          timeStyle: "short"
        }).format(new Date(data.timestamp))}
      </p>
    </div>
  );
}
