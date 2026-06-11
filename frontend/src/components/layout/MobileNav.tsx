"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { MouseEventHandler } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Radar, X } from "lucide-react";

import { env } from "@/lib/env";
import { isActiveRoute, primaryNav, utilityNav, type NavItem } from "@/lib/nav";
import { cn } from "@/lib/utils";

/**
 * Mobile navigation: a hamburger button that opens an accessible slide-in drawer.
 * Replaces the old horizontally-scrolling pill row (which clipped routes off the
 * edge on a phone) with a modern, thumb-reachable sheet listing every
 * destination. Visible only below the `lg` breakpoint, where the desktop top bar
 * is hidden.
 *
 * Accessibility mirrors the command palette: Escape closes, body scroll is locked
 * while open, focus moves into the drawer and is restored on close, and Tab is
 * trapped inside. The drawer is only mounted while open, so its links are never
 * in the tab order behind a closed sheet.
 */
export function MobileNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label="Open navigation menu"
        className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--panel-border)] bg-[#111722] text-[var(--muted)] transition-colors hover:border-[#4d5c73] hover:text-[#fff8df] lg:hidden"
        onClick={() => setOpen(true)}
        type="button"
      >
        <Menu className="h-5 w-5" />
      </button>
      {open ? <MobileNavDrawer pathname={pathname} onClose={() => setOpen(false)} /> : null}
    </>
  );
}

function MobileNavDrawer({ pathname, onClose }: { pathname: string; onClose: () => void }) {
  // `entered` drives the enter/exit transition; closing flips it false, then the
  // parent unmounts after the slide-out completes.
  const [entered, setEntered] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const requestClose = useCallback(() => {
    setEntered(false);
    closeTimer.current = setTimeout(onClose, 220);
  }, [onClose]);

  useEffect(() => {
    // Slide in on the next frame so the transition runs from the off-screen state.
    const raf = requestAnimationFrame(() => {
      setEntered(true);
      closeButtonRef.current?.focus();
    });

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        requestClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);

    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(closeTimer.current);
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, [requestClose]);

  // Keep Tab focus inside the drawer while it is open.
  function trapFocus(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "Tab" || !panelRef.current) {
      return;
    }
    const focusable = panelRef.current.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    if (focusable.length === 0) {
      return;
    }
    const first = focusable[0]!;
    const last = focusable[focusable.length - 1]!;
    const active = document.activeElement;
    if (event.shiftKey && active === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }

  // Portal to <body> so the fixed overlay escapes the header's containing block:
  // the header sets `backdrop-filter`, which would otherwise trap this fixed
  // element inside the ~64px-tall header box (the command palette avoids this by
  // rendering at the app root, not inside the header).
  if (typeof document === "undefined") {
    return null;
  }

  return createPortal(
    <div
      aria-hidden={!entered}
      className="fixed inset-0 z-50 lg:hidden"
      onKeyDown={trapFocus}
      role="presentation"
    >
      {/* Backdrop */}
      <div
        className={cn(
          "absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-200",
          entered ? "opacity-100" : "opacity-0"
        )}
        onClick={requestClose}
      />

      {/* Sliding panel */}
      <div
        aria-label="Navigation"
        aria-modal="true"
        className={cn(
          "absolute inset-y-0 right-0 flex w-[86%] max-w-[340px] flex-col border-l border-[#253047] bg-[#0a0f17] shadow-[0_0_60px_rgba(0,0,0,0.55)] transition-transform duration-200 ease-out",
          entered ? "translate-x-0" : "translate-x-full"
        )}
        ref={panelRef}
        role="dialog"
      >
        <div className="flex items-center justify-between gap-3 border-b border-[#1d2738] px-4 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[#6f5620] bg-[#151006] text-[var(--gold-strong)]">
              <Radar className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-[#fff8df]">
                {env.NEXT_PUBLIC_APP_NAME}
              </p>
              <p className="text-xs text-[#99a3b4]">AI market command</p>
            </div>
          </div>
          <button
            aria-label="Close navigation menu"
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--panel-border)] bg-[#111722] text-[var(--muted)] transition-colors hover:border-[#4d5c73] hover:text-[#fff8df]"
            onClick={requestClose}
            ref={closeButtonRef}
            type="button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav
          aria-label="Primary"
          className="flex-1 overflow-y-auto px-3 py-4"
        >
          <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#5b6678]">
            Navigate
          </p>
          <ul className="space-y-1.5">
            {primaryNav.map((item) => (
              <li key={item.href}>
                <DrawerLink item={item} pathname={pathname} onNavigate={requestClose} />
              </li>
            ))}
          </ul>

          <div className="my-4 h-px bg-[#1a2334]" />

          <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#5b6678]">
            More
          </p>
          <ul className="space-y-1.5">
            {utilityNav.map((item) => (
              <li key={item.href}>
                <DrawerLink item={item} pathname={pathname} onNavigate={requestClose} />
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </div>,
    document.body
  );
}

function DrawerLink({
  item,
  pathname,
  onNavigate
}: {
  item: NavItem;
  pathname: string;
  onNavigate: MouseEventHandler<HTMLAnchorElement>;
}) {
  const Icon = item.icon;
  const isActive = isActiveRoute(pathname, item.href);

  return (
    <Link
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "flex items-center gap-3 rounded-xl border px-3 py-3 transition-colors",
        isActive
          ? "border-[#7a5f1f] bg-[#1a1407]"
          : "border-transparent hover:border-[#26324a] hover:bg-[#0f1622]"
      )}
      href={item.href}
      onClick={onNavigate}
    >
      <span
        className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border",
          isActive
            ? "border-[#8f6a20] bg-[#241b08] text-[var(--gold-strong)]"
            : "border-[#26324a] bg-[#0f1622] text-[#9aa4b2]"
        )}
      >
        <Icon aria-hidden className="h-5 w-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span
          className={cn(
            "block text-sm font-semibold",
            isActive ? "text-[#fff8df]" : "text-[#dce3ee]"
          )}
        >
          {item.label}
        </span>
        <span className="block truncate text-xs text-[var(--muted)]">{item.description}</span>
      </span>
      {isActive ? (
        <span aria-hidden className="h-2 w-2 shrink-0 rounded-full bg-[var(--gold-strong)]" />
      ) : null}
    </Link>
  );
}
