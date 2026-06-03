"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  BarChart3,
  CornerDownLeft,
  Gauge,
  type LucideIcon,
  PlayCircle,
  Search,
  TrendingUp
} from "lucide-react";

import { usePairsQuery, useSignalsQuery, useTriggerAnalysisRun } from "@/hooks/useTradeQueries";
import { track } from "@/lib/analytics";
import { cn } from "@/lib/utils";
import { toast } from "@/store/toastStore";
import { useUIStore } from "@/store/uiStore";

type CommandGroup = "Actions" | "Pairs" | "Signals";

type CommandItem = {
  id: string;
  label: string;
  hint: string;
  group: CommandGroup;
  icon: LucideIcon;
  keywords: string;
  run: () => void;
};

const GROUP_ORDER: CommandGroup[] = ["Actions", "Pairs", "Signals"];

/**
 * Outer controller: owns the global Cmd/Ctrl+K + Esc shortcuts and the open
 * state. The dialog body is only mounted while open, so its search/selection
 * state resets cleanly on each launch without reset-in-effect churn.
 */
export function CommandPalette() {
  const open = useUIStore((state) => state.isCommandPaletteOpen);
  const setOpen = useUIStore((state) => state.setCommandPaletteOpen);
  const toggle = useUIStore((state) => state.toggleCommandPalette);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        toggle();
      } else if (event.key === "Escape") {
        setOpen(false);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toggle, setOpen]);

  useEffect(() => {
    if (open) {
      track({ name: "command_palette_open" });
    }
  }, [open]);

  if (!open) {
    return null;
  }

  return <CommandPaletteDialog onClose={() => setOpen(false)} />;
}

function CommandPaletteDialog({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const pairsQuery = usePairsQuery();
  const { signalsQuery } = useSignalsQuery();
  const trigger = useTriggerAnalysisRun();

  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const dialogRef = useRef<HTMLDivElement>(null);

  // Return focus to whatever was focused before the palette opened.
  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    return () => previouslyFocused?.focus?.();
  }, []);

  const items = useMemo<CommandItem[]>(() => {
    const navigate = (href: string) => () => {
      onClose();
      router.push(href);
    };

    const actions: CommandItem[] = [
      {
        id: "nav-dashboard",
        label: "Go to Dashboard",
        hint: "Overview",
        group: "Actions",
        icon: Gauge,
        keywords: "dashboard home overview",
        run: navigate("/dashboard")
      },
      {
        id: "nav-signals",
        label: "Browse Signals",
        hint: "All setups",
        group: "Actions",
        icon: Activity,
        keywords: "signals browse setups",
        run: navigate("/signals")
      },
      {
        id: "nav-analysis",
        label: "Analysis Runs",
        hint: "Run ledger",
        group: "Actions",
        icon: BarChart3,
        keywords: "analysis runs ledger pipeline",
        run: navigate("/analysis")
      },
      {
        id: "action-trigger",
        label: "Trigger analysis run",
        hint: "Manual run",
        group: "Actions",
        icon: PlayCircle,
        keywords: "trigger run analyze refresh pipeline",
        run: () => {
          onClose();
          trigger.mutate(undefined, {
            onSuccess: () => {
              track({ name: "analysis_run_triggered", source: "command-palette" });
              toast({
                tone: "success",
                title: "Analysis run scheduled",
                description: "Track it on the Analysis page as it completes."
              });
            },
            onError: (error) =>
              toast({
                tone: "danger",
                title: "Could not trigger run",
                description: error instanceof Error ? error.message : "Unexpected error."
              })
          });
        }
      }
    ];

    const pairItems: CommandItem[] = (pairsQuery.data ?? []).map((pair) => ({
      id: `pair-${pair.symbol}`,
      label: pair.symbol,
      hint: pair.displayName,
      group: "Pairs",
      icon: TrendingUp,
      keywords: `${pair.symbol} ${pair.displayName} pair`,
      run: navigate(`/pairs/${pair.symbol}`)
    }));

    const signalItems: CommandItem[] = (signalsQuery.data?.signals ?? [])
      .slice(0, 12)
      .map((signal) => ({
        id: `signal-${signal.id}`,
        label: `${signal.symbol} · ${signal.direction.toUpperCase()}`,
        hint: `${Math.round(signal.confidence * 100)}% confidence`,
        group: "Signals",
        icon: Activity,
        keywords: `${signal.symbol} ${signal.direction} signal ${signal.id}`,
        run: navigate(`/signals/${signal.id}`)
      }));

    return [...actions, ...pairItems, ...signalItems];
  }, [pairsQuery.data, signalsQuery.data, router, onClose, trigger]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) {
      return items;
    }

    return items.filter((item) => item.keywords.toLowerCase().includes(term));
  }, [items, query]);

  // Clamp at use-time so a shrinking result set never points past the end.
  const safeIndex = filtered.length === 0 ? 0 : Math.min(activeIndex, filtered.length - 1);

  function onInputKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex(Math.min(safeIndex + 1, filtered.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex(Math.max(safeIndex - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      filtered[safeIndex]?.run();
    }
  }

  // Keep Tab focus inside the dialog while it is open.
  function trapFocus(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "Tab" || !dialogRef.current) {
      return;
    }

    const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input, [tabindex]:not([tabindex="-1"])'
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

  return (
    <div
      aria-label="Command palette"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 px-4 pt-[12vh] backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
    >
      <div
        className="w-full max-w-xl overflow-hidden rounded-xl border border-[var(--panel-border)] bg-[#0d131c] shadow-[var(--surface-shadow)]"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={trapFocus}
        ref={dialogRef}
      >
        <div className="flex items-center gap-3 border-b border-[var(--panel-border)] px-4">
          <Search className="h-4 w-4 text-[var(--muted)]" />
          <input
            autoFocus
            className="h-12 w-full bg-transparent text-sm text-[#fff8df] outline-none placeholder:text-[var(--muted)]"
            onChange={(event) => {
              setQuery(event.target.value);
              setActiveIndex(0);
            }}
            onKeyDown={onInputKeyDown}
            placeholder="Search pairs, signals, or actions…"
            value={query}
          />
          <kbd className="rounded border border-[var(--panel-border)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--muted)]">
            ESC
          </kbd>
        </div>

        <div className="max-h-[50vh] overflow-y-auto py-2">
          {filtered.length > 0 ? (
            GROUP_ORDER.map((group) => {
              const groupItems = filtered.filter((item) => item.group === group);
              if (groupItems.length === 0) {
                return null;
              }

              return (
                <div className="px-2 py-1" key={group}>
                  <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                    {group}
                  </p>
                  {groupItems.map((item) => {
                    const index = filtered.indexOf(item);
                    const Icon = item.icon;
                    const isActive = index === safeIndex;

                    return (
                      <button
                        className={cn(
                          "flex w-full items-center gap-3 rounded-md px-2 py-2 text-left transition-colors",
                          isActive ? "bg-[#182132]" : "hover:bg-[#101722]"
                        )}
                        key={item.id}
                        onClick={item.run}
                        onMouseEnter={() => setActiveIndex(index)}
                        type="button"
                      >
                        <Icon className="h-4 w-4 text-[var(--gold)]" />
                        <span className="flex-1 text-sm font-medium text-[#fff8df]">
                          {item.label}
                        </span>
                        <span className="text-xs text-[var(--muted)]">{item.hint}</span>
                      </button>
                    );
                  })}
                </div>
              );
            })
          ) : (
            <p className="px-4 py-8 text-center text-sm text-[var(--muted)]">
              No matches for “{query}”.
            </p>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-[var(--panel-border)] px-4 py-2 text-[11px] text-[var(--muted)]">
          <span className="inline-flex items-center gap-1">
            <CornerDownLeft className="h-3 w-3" /> to select
          </span>
          <span>↑ ↓ to navigate</span>
        </div>
      </div>
    </div>
  );
}
