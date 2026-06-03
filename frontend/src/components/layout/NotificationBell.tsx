"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bell, BellRing, Check } from "lucide-react";

import { RelativeTime } from "@/components/common/RelativeTime";
import { Button } from "@/components/ui/Button";
import { useSignalsQuery } from "@/hooks/useTradeQueries";
import { track } from "@/lib/analytics";
import { cn } from "@/lib/utils";
import { useNotificationStore } from "@/store/notificationStore";
import { toast } from "@/store/toastStore";

/**
 * Notifications bell: watches the live signal feed, raises a toast + feed entry
 * for genuinely new signals, and exposes the feed in a dropdown with an unread
 * count badge.
 */
export function NotificationBell() {
  const { signalsQuery } = useSignalsQuery();
  const registerSignals = useNotificationStore((state) => state.registerSignals);
  const notifications = useNotificationStore((state) => state.notifications);
  const markAllRead = useNotificationStore((state) => state.markAllRead);

  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const unreadCount = notifications.filter((item) => !item.read).length;

  // Reconcile new signals into notifications + toasts whenever the feed updates.
  const signals = signalsQuery.data?.signals;
  useEffect(() => {
    if (!signals) {
      return;
    }

    const created = registerSignals(signals);
    if (created.length === 0) {
      return;
    }

    track({ name: "signal_notification", count: created.length });
    created.slice(0, 3).forEach((notification) => {
      toast({
        tone: "info",
        title: notification.title,
        description: notification.description,
        href: notification.href
      });
    });
  }, [signals, registerSignals]);

  // Close the dropdown on outside click or Escape.
  useEffect(() => {
    if (!open) {
      return;
    }

    function onPointerDown(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  function toggle() {
    setOpen((value) => {
      const next = !value;
      if (next && unreadCount > 0) {
        markAllRead();
      }
      return next;
    });
  }

  return (
    <div className="relative" ref={containerRef}>
      <Button
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : "Notifications"}
        onClick={toggle}
        size="icon"
        variant="secondary"
      >
        {unreadCount > 0 ? <BellRing className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--red)] px-1 text-[10px] font-semibold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </Button>

      {open ? (
        <div className="absolute right-0 z-40 mt-2 w-80 overflow-hidden rounded-lg border border-[var(--panel-border)] bg-[#0d131c] shadow-[var(--surface-shadow)]">
          <div className="flex items-center justify-between border-b border-[var(--panel-border)] px-4 py-3">
            <p className="text-sm font-semibold text-[#fff8df]">Notifications</p>
            {notifications.length > 0 ? (
              <button
                className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--blue-strong)] hover:text-[#8ab8ff]"
                onClick={markAllRead}
                type="button"
              >
                <Check className="h-3.5 w-3.5" />
                Mark all read
              </button>
            ) : null}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {notifications.length > 0 ? (
              notifications.map((item) => (
                <Link
                  className={cn(
                    "block border-b border-[var(--panel-border)] px-4 py-3 transition-colors hover:bg-[#101722]",
                    !item.read && "bg-[#10243d]/40"
                  )}
                  href={item.href}
                  key={item.id}
                  onClick={() => setOpen(false)}
                >
                  <p className="text-sm font-semibold text-[#fff8df]">{item.title}</p>
                  <p className="mt-1 text-xs text-[var(--muted)]">{item.description}</p>
                  <RelativeTime
                    className="mt-1 block text-[11px] text-[#6f7b8e]"
                    intervalMs={30_000}
                    value={item.createdAt}
                  />
                </Link>
              ))
            ) : (
              <p className="px-4 py-6 text-center text-sm text-[var(--muted)]">
                No notifications yet. New signals will appear here.
              </p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
