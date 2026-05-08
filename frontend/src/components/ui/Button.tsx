import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "icon";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "border-[#8f6a20] bg-[var(--gold)] text-[#0a0c10] shadow-sm hover:bg-[var(--gold-strong)]",
  secondary:
    "border-[var(--panel-border)] bg-[#111722] text-[var(--foreground)] hover:border-[#4d5c73] hover:bg-[#182132]",
  ghost:
    "border-transparent bg-transparent text-[var(--muted)] hover:bg-[#151d2a] hover:text-[var(--foreground)]",
  danger: "border-[#7a2028] bg-[var(--red)] text-white hover:bg-[var(--red-strong)]"
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-9 gap-2 px-3 text-sm",
  md: "h-10 gap-2.5 px-4 text-sm",
  icon: "h-10 w-10 justify-center p-0"
};

export function Button({
  className,
  variant = "secondary",
  size = "md",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg border font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--gold)] disabled:cursor-not-allowed disabled:opacity-50",
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      type={type}
      {...props}
    />
  );
}
