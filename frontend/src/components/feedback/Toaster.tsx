"use client";

import Link from "next/link";
import { CheckCircle2, Info, TriangleAlert, X } from "lucide-react";

import { useToastStore, type ToastTone } from "@/store/toastStore";

const toneConfig: Record<ToastTone, { icon: typeof Info; border: string; accent: string }> = {
  info: { icon: Info, border: "border-[#234f86]", accent: "text-[var(--blue-strong)]" },
  success: { icon: CheckCircle2, border: "border-[#6f5620]", accent: "text-[var(--gold-strong)]" },
  danger: { icon: TriangleAlert, border: "border-[#6e2029]", accent: "text-[var(--red-strong)]" }
};

/** Fixed-position stack of ephemeral toasts. Mounted once in the app shell. */
export function Toaster() {
  const toasts = useToastStore((state) => state.toasts);
  const dismissToast = useToastStore((state) => state.dismissToast);

  if (toasts.length === 0) {
    return null;
  }

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-3"
    >
      {toasts.map((item) => {
        const config = toneConfig[item.tone];
        const Icon = config.icon;

        return (
          <div
            className={`pointer-events-auto rounded-lg border ${config.border} bg-[#0d131c] p-4 shadow-[var(--surface-shadow)]`}
            key={item.id}
            role="status"
          >
            <div className="flex items-start gap-3">
              <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${config.accent}`} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-[#fff8df]">{item.title}</p>
                {item.description ? (
                  <p className="mt-1 text-sm leading-6 text-[var(--muted)]">{item.description}</p>
                ) : null}
                {item.href ? (
                  <Link
                    className="mt-2 inline-block text-sm font-semibold text-[var(--blue-strong)] hover:text-[#8ab8ff]"
                    href={item.href}
                    onClick={() => dismissToast(item.id)}
                  >
                    View
                  </Link>
                ) : null}
              </div>
              <button
                aria-label="Dismiss notification"
                className="shrink-0 text-[var(--muted)] transition-colors hover:text-[#fff8df]"
                onClick={() => dismissToast(item.id)}
                type="button"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
