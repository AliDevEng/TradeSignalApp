import { create } from "zustand";

type DashboardView = "overview" | "signals" | "risk";
type Density = "comfortable" | "compact";

type UIState = {
  dashboardView: DashboardView;
  density: Density;
  isCommandPanelOpen: boolean;
  setDashboardView: (view: DashboardView) => void;
  setDensity: (density: Density) => void;
  toggleCommandPanel: () => void;
};

export const useUIStore = create<UIState>((set) => ({
  dashboardView: "overview",
  density: "comfortable",
  isCommandPanelOpen: false,
  setDashboardView: (dashboardView) => set({ dashboardView }),
  setDensity: (density) => set({ density }),
  toggleCommandPanel: () =>
    set((state) => ({ isCommandPanelOpen: !state.isCommandPanelOpen }))
}));
