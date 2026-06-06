import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import type { Signal } from "@/types/signal";

export type AppNotification = {
  id: string;
  title: string;
  description: string;
  href: string;
  createdAt: string;
  read: boolean;
};

type NotificationState = {
  notifications: AppNotification[];
  /** Signal ids already surfaced, persisted so reloads don't re-announce. */
  seenSignalIds: string[];
  /** Whether the seen-set has been seeded from a first signal load. */
  initialized: boolean;
  markAllRead: () => void;
  clear: () => void;
  /**
   * Reconcile the latest signals against what we've seen. The first call only
   * seeds the seen-set (no notifications) so a returning user isn't flooded;
   * later calls announce genuinely new signals.
   */
  registerSignals: (signals: Signal[]) => AppNotification[];
  /**
   * Push a notification raised by the real-time stream. Deduped by notification
   * id (so a poll/stream race can't double-announce). When `markSeenSignalId` is
   * given, that signal id is also recorded as seen so the polling path
   * ({@link registerSignals}) won't re-announce the same new signal. Returns
   * whether a new notification was added.
   */
  pushLiveNotification: (notification: AppNotification, markSeenSignalId?: string) => boolean;
};

const MAX_NOTIFICATIONS = 30;

function toNotification(signal: Signal): AppNotification {
  const direction = signal.direction.toUpperCase();
  return {
    id: signal.id,
    title: `New ${direction} signal · ${signal.symbol}`,
    description: `${Math.round(signal.confidence * 100)}% confidence on ${signal.timeframe.toUpperCase()}`,
    href: `/signals/${signal.id}`,
    createdAt: signal.generatedAt,
    read: false
  };
}

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      notifications: [],
      seenSignalIds: [],
      initialized: false,
      markAllRead: () =>
        set((state) => ({
          notifications: state.notifications.map((item) => ({ ...item, read: true }))
        })),
      clear: () => set({ notifications: [] }),
      registerSignals: (signals) => {
        const { seenSignalIds, initialized, notifications } = get();
        const seen = new Set(seenSignalIds);
        const fresh = signals.filter((signal) => !seen.has(signal.id));

        if (fresh.length === 0) {
          return [];
        }

        const allSeen = [...seenSignalIds, ...fresh.map((signal) => signal.id)];

        // First load: seed silently so we don't announce the existing backlog.
        if (!initialized) {
          set({ seenSignalIds: allSeen, initialized: true });
          return [];
        }

        const created = fresh.map(toNotification);
        set({
          notifications: [...created, ...notifications].slice(0, MAX_NOTIFICATIONS),
          seenSignalIds: allSeen
        });

        return created;
      },
      pushLiveNotification: (notification, markSeenSignalId) => {
        const { notifications, seenSignalIds } = get();

        // Already in the feed → no-op (a poll/stream race, or a duplicate frame).
        if (notifications.some((item) => item.id === notification.id)) {
          if (markSeenSignalId && !seenSignalIds.includes(markSeenSignalId)) {
            set({ seenSignalIds: [...seenSignalIds, markSeenSignalId] });
          }
          return false;
        }
        // The polling path already announced this signal — don't repeat it.
        if (markSeenSignalId && seenSignalIds.includes(markSeenSignalId)) {
          return false;
        }

        set({
          notifications: [notification, ...notifications].slice(0, MAX_NOTIFICATIONS),
          seenSignalIds: markSeenSignalId
            ? [...seenSignalIds, markSeenSignalId]
            : seenSignalIds
        });
        return true;
      }
    }),
    {
      name: "tradesignal-notifications",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        notifications: state.notifications,
        seenSignalIds: state.seenSignalIds,
        initialized: state.initialized
      }),
      // Rehydrated after mount via StoreHydration to avoid SSR mismatches.
      skipHydration: true
    }
  )
);
