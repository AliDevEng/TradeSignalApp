import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export default function Loading() {
  return (
    <div className="rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] p-8">
      <LoadingSpinner label="Loading workspace" />
    </div>
  );
}
