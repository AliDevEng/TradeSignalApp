import { cn } from "@/lib/utils";

type LoadingSpinnerProps = {
  className?: string;
  label?: string;
};

export function LoadingSpinner({ className, label = "Loading" }: LoadingSpinnerProps) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-[var(--muted)]">
      <span
        aria-hidden="true"
        className={cn(
          "h-4 w-4 animate-spin rounded-full border-2 border-[#344053] border-t-[var(--gold)]",
          className
        )}
      />
      <span>{label}</span>
    </span>
  );
}
