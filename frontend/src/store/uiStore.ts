import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type Density = "comfortable" | "compact";

type UIState = {
  density: Density;
  /** Last route the user visited, restored across sessions for quick re-entry. */
  lastPath: string | null;
  isCommandPaletteOpen: boolean;
  setDensity: (density: Density) => void;
  setLastPath: (path: string) => void;
  toggleCommandPalette: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
};

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      density: "comfortable",
      lastPath: null,
      isCommandPaletteOpen: false,
      setDensity: (density) => set({ density }),
      setLastPath: (lastPath) => set({ lastPath }),
      toggleCommandPalette: () =>
        set((state) => ({ isCommandPaletteOpen: !state.isCommandPaletteOpen })),
      setCommandPaletteOpen: (isCommandPaletteOpen) => set({ isCommandPaletteOpen })
    }),
    {
      name: "tradesignal-ui",
      storage: createJSONStorage(() => localStorage),
      // Only durable preferences are persisted; transient palette state is not.
      partialize: (state) => ({ density: state.density, lastPath: state.lastPath }),
      // Rehydrate after mount (see StoreHydration) so SSR markup matches the
      // first client render and React doesn't flag a hydration mismatch.
      skipHydration: true
    }
  )
);
