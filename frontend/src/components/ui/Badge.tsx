import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
};

const toneStyles: Record<BadgeTone, string> = {
  neutral: "border-[#344053] bg-[#141b27] text-[#cbd5e1]",
  success: "border-[#6f5620] bg-[var(--gold-soft)] text-[var(--gold-strong)]",
  warning: "border-[#6f5620] bg-[#1f1a10] text-[var(--gold)]",
  danger: "border-[#6e2029] bg-[var(--red-soft)] text-[var(--red-strong)]",
  info: "border-[#234f86] bg-[var(--blue-soft)] text-[var(--blue-strong)]"
};

export function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide",
        toneStyles[tone],
        className
      )}
      {...props}
    />
  );
}
