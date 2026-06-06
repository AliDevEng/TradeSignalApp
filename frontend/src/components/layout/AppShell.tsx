"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  ChevronRight,
  CircleCheckBig,
  Command,
  Gauge,
  LineChart,
  Menu,
  Radar,
  Settings,
  ShieldCheck
} from "lucide-react";

import { CommandPalette } from "@/components/layout/CommandPalette";
import { LiveIndicator } from "@/components/layout/LiveIndicator";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { StoreHydration } from "@/components/layout/StoreHydration";
import { Toaster } from "@/components/feedback/Toaster";
import { Button } from "@/components/ui/Button";
import { useEventStream } from "@/hooks/useEventStream";
import { track } from "@/lib/analytics";
import { env } from "@/lib/env";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/store/uiStore";

type AppShellProps = Readonly<{
  children: React.ReactNode;
}>;

const navigationItems = [
  { label: "Dashboard", href: "/dashboard", icon: Gauge },
  { label: "Signals", href: "/signals", icon: Activity },
  { label: "Analysis", href: "/analysis", icon: BarChart3 },
  { label: "Closed", href: "/closed", icon: CircleCheckBig },
  { label: "Performance", href: "/performance", icon: LineChart },
  { label: "Risk", href: "/signals?status=active&sort=confidence", icon: ShieldCheck },
  { label: "Settings", href: "/settings", icon: Settings }
] as const;

function isActiveRoute(pathname: string, href: string): boolean {
  const route = href.split("?")[0];

  if (route === "/dashboard") {
    return pathname === "/" || pathname === "/dashboard";
  }

  return pathname === route || pathname.startsWith(`${route}/`);
}

function labelForSegment(segment: string): string {
  const decoded = decodeURIComponent(segment);

  if (/^[0-9a-f-]{24,}$/i.test(decoded) || decoded.startsWith("sig-")) {
    return "Detail";
  }

  return decoded
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function Breadcrumbs({ pathname }: { pathname: string }) {
  const normalizedPath = pathname === "/" ? "/dashboard" : pathname;
  const segments = normalizedPath.split("/").filter(Boolean);

  return (
    <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-1 text-sm">
      <Link className="font-medium text-[var(--muted)] hover:text-[#fff8df]" href="/dashboard">
        Home
      </Link>
      {segments.map((segment, index) => {
        const href = `/${segments.slice(0, index + 1).join("/")}`;
        const isCurrent = index === segments.length - 1;

        if (segment === "dashboard") {
          return null;
        }

        return (
          <span className="inline-flex items-center gap-1" key={href}>
            <ChevronRight className="h-3.5 w-3.5 text-[#566174]" />
            {isCurrent ? (
              <span className="font-semibold text-[#fff8df]">{labelForSegment(segment)}</span>
            ) : (
              <Link className="font-medium text-[var(--muted)] hover:text-[#fff8df]" href={href}>
                {labelForSegment(segment)}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const toggleCommandPalette = useUIStore((state) => state.toggleCommandPalette);
  const setLastPath = useUIStore((state) => state.setLastPath);
  // Open the real-time stream for the whole app session; surface its state in the
  // header so the user knows whether updates are live or polled.
  const streamStatus = useEventStream();

  useEffect(() => {
    setLastPath(pathname);
    track({ name: "pageview", path: pathname });
  }, [pathname, setLastPath]);

  return (
    <div className="min-h-dvh overflow-x-hidden bg-[var(--background)]">
      <a
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:border focus:border-[var(--gold)] focus:bg-[#0d131c] focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-[#fff8df]"
        href="#main-content"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b border-[#253047] bg-[rgba(9,11,16,0.92)] shadow-[0_16px_40px_rgba(0,0,0,0.24)] backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 w-full max-w-[1480px] items-center justify-between gap-3 px-3 sm:px-5">
          <Link className="flex min-w-0 items-center gap-3" href="/dashboard">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[#6f5620] bg-[#151006] text-[var(--gold-strong)] shadow-[0_0_24px_rgba(216,175,79,0.16)]">
              <Radar className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-[#fff8df]">
                {env.NEXT_PUBLIC_APP_NAME}
              </p>
              <p className="hidden text-xs text-[#99a3b4] sm:block">AI market command</p>
            </div>
          </Link>

          <nav className="hidden items-center rounded-lg border border-[#293244] bg-[#101722] p-1 lg:flex">
            {navigationItems.slice(0, 5).map((item) => {
              const Icon = item.icon;
              const isActive = isActiveRoute(pathname, item.href);

              return (
                <Link
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex h-9 items-center gap-2 rounded-md px-3 text-sm font-semibold transition-colors",
                    isActive
                      ? "bg-[var(--gold)] text-[#080a0f]"
                      : "text-[#9aa4b2] hover:bg-[#182132] hover:text-[#fff8df]"
                  )}
                  href={item.href}
                  key={item.href}
                >
                  <Icon aria-hidden className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-2">
            <Button
              aria-label="Open command palette"
              className="gap-2"
              onClick={toggleCommandPalette}
              variant="secondary"
            >
              <Command className="h-4 w-4" />
              <span className="hidden text-xs text-[var(--muted)] sm:inline">Ctrl K</span>
            </Button>
            <LiveIndicator status={streamStatus} />
            <NotificationBell />
          </div>
        </div>

        <nav
          aria-label="Primary"
          className="mx-auto flex w-full max-w-[1480px] gap-2 overflow-x-auto px-3 pb-3 sm:px-5 lg:hidden"
        >
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const isActive = isActiveRoute(pathname, item.href);

            return (
              <Link
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "inline-flex h-10 shrink-0 items-center gap-2 rounded-lg border px-3 text-sm font-semibold transition-colors",
                  isActive
                    ? "border-[#8f6a20] bg-[var(--gold)] text-[#080a0f]"
                    : "border-[#263247] bg-[#101722] text-[#a5afbf] hover:border-[#4d5c73] hover:text-[#fff8df]"
                )}
                href={item.href}
                key={item.href}
              >
                <Icon aria-hidden className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>

      <div className="mx-auto grid w-full max-w-[1480px] gap-5 px-3 py-5 sm:px-5 xl:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="hidden xl:block">
          <div className="sticky top-24 space-y-3">
            <div className="rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] p-3 shadow-[var(--surface-shadow)]">
              <div className="mb-3 flex items-center gap-2 px-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                <Menu className="h-4 w-4 text-[var(--gold)]" />
                Workspace
              </div>
              <nav className="space-y-1" aria-label="Primary">
                {navigationItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = isActiveRoute(pathname, item.href);

                  return (
                    <Link
                      aria-current={isActive ? "page" : undefined}
                      className={cn(
                        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold transition-colors",
                        isActive
                          ? "bg-[#201a0d] text-[var(--gold-strong)]"
                          : "text-[#a5afbf] hover:bg-[#182132] hover:text-[#fff8df]"
                      )}
                      href={item.href}
                      key={item.href}
                    >
                      <Icon aria-hidden className="h-4 w-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>
          </div>
        </aside>

        <main className="min-w-0 space-y-5" id="main-content" tabIndex={-1}>
          <Breadcrumbs pathname={pathname} />
          {children}
        </main>
      </div>

      <StoreHydration />
      <CommandPalette />
      <Toaster />
    </div>
  );
}
