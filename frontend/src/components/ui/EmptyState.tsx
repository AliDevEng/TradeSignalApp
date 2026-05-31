import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

export function EmptyState({ action, description, title }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-[#45536a] bg-[var(--panel)] p-8 text-center">
      <h3 className="text-lg font-semibold text-[#fff8df]">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--muted)]">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
