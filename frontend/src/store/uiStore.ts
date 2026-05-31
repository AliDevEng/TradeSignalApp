import { create } from "zustand";

type Density = "comfortable" | "compact";

type UIState = {
  density: Density;
  isCommandPanelOpen: boolean;
  setDensity: (density: Density) => void;
  toggleCommandPanel: () => void;
};

export const useUIStore = create<UIState>((set) => ({
  density: "comfortable",
  isCommandPanelOpen: false,
  setDensity: (density) => set({ density }),
  toggleCommandPanel: () =>
    set((state) => ({ isCommandPanelOpen: !state.isCommandPanelOpen }))
}));
