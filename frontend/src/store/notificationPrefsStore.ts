import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import type { SignalTradeStyle } from "@/types/signal";

/**
 * Client-side notification preferences — the in-app surfacing policy. They mirror
 * the backend's server-side {@link NotificationPreferences} (which governs
 * off-platform Telegram delivery), but apply only to what *this browser* raises
 * as toasts + feed entries from the live stream. Cache invalidation always runs
 * regardless, so the views stay fresh even when notifications are muted.
 *
 * Persisted to `localStorage` so the choice survives reloads, rehydrated after
 * mount (see {@link StoreHydration}) to avoid SSR markup mismatches.
 */
export type NotificationPrefsState = {
  /** Master switch for in-app stream toasts + feed entries. */
  enabled: boolean;
  /** Minimum stated confidence (0..1) for a new-signal notification. */
  minConfidence: number;
  /** Styles that may notify. Empty = no style filter (all allowed). */
  styles: SignalTradeStyle[];
  /** Only notify for actionable (`should_trade`) new signals. */
  onlyActionable: boolean;
  /** Per-event toggles, matching the two notifying event types. */
  onSignalCreated: boolean;
  onSignalClosed: boolean;
  setEnabled: (enabled: boolean) => void;
  setMinConfidence: (value: number) => void;
  toggleStyle: (style: SignalTradeStyle) => void;
  setOnlyActionable: (value: boolean) => void;
  setOnSignalCreated: (value: boolean) => void;
  setOnSignalClosed: (value: boolean) => void;
  reset: () => void;
};

/** Conservative defaults mirroring the backend policy (min 0.7, both styles). */
export const DEFAULT_NOTIFICATION_PREFS = {
  enabled: true,
  minConfidence: 0.7,
  styles: ["scalp", "swing"] as SignalTradeStyle[],
  onlyActionable: true,
  onSignalCreated: true,
  onSignalClosed: true
} as const;

export const useNotificationPrefsStore = create<NotificationPrefsState>()(
  persist(
    (set) => ({
      ...DEFAULT_NOTIFICATION_PREFS,
      styles: [...DEFAULT_NOTIFICATION_PREFS.styles],
      setEnabled: (enabled) => set({ enabled }),
      setMinConfidence: (minConfidence) =>
        set({ minConfidence: Math.min(1, Math.max(0, minConfidence)) }),
      toggleStyle: (style) =>
        set((state) => ({
          styles: state.styles.includes(style)
            ? state.styles.filter((value) => value !== style)
            : [...state.styles, style]
        })),
      setOnlyActionable: (onlyActionable) => set({ onlyActionable }),
      setOnSignalCreated: (onSignalCreated) => set({ onSignalCreated }),
      setOnSignalClosed: (onSignalClosed) => set({ onSignalClosed }),
      reset: () =>
        set({ ...DEFAULT_NOTIFICATION_PREFS, styles: [...DEFAULT_NOTIFICATION_PREFS.styles] })
    }),
    {
      name: "tradesignal-notification-prefs",
      storage: createJSONStorage(() => localStorage),
      skipHydration: true
    }
  )
);
