"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Bell,
  Bot,
  ChevronRight,
  Command,
  Gauge,
  Radar,
  ShieldCheck
} from "lucide-react";

import { Button } from "@/components/ui/Button";
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
  { label: "Risk", href: "/signals?status=active&sort=confidence", icon: ShieldCheck }
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
  const toggleCommandPanel = useUIStore((state) => state.toggleCommandPanel);

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="sticky top-0 z-30 border-b border-[#2b2415] bg-[rgba(9,11,16,0.94)] backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 w-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link className="flex items-center gap-3" href="/dashboard">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#6f5620] bg-[#151006] text-[var(--gold-strong)] shadow-[0_0_24px_rgba(216,175,79,0.16)]">
              <Radar className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#fff8df]">{env.NEXT_PUBLIC_APP_NAME}</p>
              <p className="text-xs text-[#99a3b4]">AI market command</p>
            </div>
          </Link>

          <nav className="hidden items-center rounded-lg border border-[#293244] bg-[#101722] p-1 md:flex">
            {navigationItems.slice(0, 3).map((item) => {
              const Icon = item.icon;
              const isActive = isActiveRoute(pathname, item.href);

              return (
                <Link
                  className={cn(
                    "flex h-9 items-center gap-2 rounded-md px-3 text-sm font-semibold transition-colors",
                    isActive
                      ? "bg-[var(--gold)] text-[#080a0f]"
                      : "text-[#9aa4b2] hover:bg-[#182132] hover:text-[#fff8df]"
                  )}
                  href={item.href}
                  key={item.href}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-2">
            <Button aria-label="Open command panel" onClick={toggleCommandPanel} size="icon">
              <Command className="h-4 w-4" />
            </Button>
            <Button aria-label="Notifications" size="icon" variant="secondary">
              <Bell className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-7xl gap-5 px-4 py-6 sm:px-6 lg:grid-cols-[260px_1fr]">
        <aside className="hidden lg:block">
          <div className="sticky top-24 space-y-3">
            <div className="rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] p-3 shadow-[var(--surface-shadow)]">
              <div className="mb-3 flex items-center gap-2 px-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                <Bot className="h-4 w-4 text-[var(--gold)]" />
                Workspace
              </div>
              <nav className="space-y-1" aria-label="Primary">
                {navigationItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = isActiveRoute(pathname, item.href);

                  return (
                    <Link
                      className={cn(
                        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold transition-colors",
                        isActive
                          ? "bg-[#201a0d] text-[var(--gold-strong)]"
                          : "text-[#a5afbf] hover:bg-[#182132] hover:text-[#fff8df]"
                      )}
                      href={item.href}
                      key={item.href}
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>
          </div>
        </aside>

        <main className="min-w-0 space-y-5">
          <Breadcrumbs pathname={pathname} />
          {children}
        </main>
      </div>
    </div>
  );
}
