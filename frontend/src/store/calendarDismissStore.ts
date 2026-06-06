import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

/**
 * Remembers which economic-calendar events the user has dismissed, so the warning
 * banner stays dismissed across reloads but a *new* event (a different key) shows
 * again. Persisted to `localStorage`; bounded so it can't grow without limit.
 */
type CalendarDismissState = {
  dismissed: string[];
  dismiss: (key: string) => void;
};

const MAX_DISMISSED = 50;

export const useCalendarDismissStore = create<CalendarDismissState>()(
  persist(
    (set) => ({
      dismissed: [],
      dismiss: (key) =>
        set((state) =>
          state.dismissed.includes(key)
            ? state
            : { dismissed: [...state.dismissed, key].slice(-MAX_DISMISSED) }
        )
    }),
    {
      name: "tradesignal-calendar-dismissed",
      storage: createJSONStorage(() => localStorage),
      skipHydration: true
    }
  )
);
