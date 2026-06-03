import { create } from "zustand";

import type { SignalDirection, SignalStatus, SignalTradeStyle } from "@/types/signal";

export type SignalSort = "confidence" | "newest" | "symbol";
export type SignalDirectionFilter = "all" | SignalDirection;
export type SignalStatusFilter = "all" | SignalStatus;
export type SignalTradeStyleFilter = "all" | SignalTradeStyle;

type SignalFilterState = {
  direction: SignalDirectionFilter;
  tradeStyle: SignalTradeStyleFilter;
  status: SignalStatusFilter;
  pair: string;
  sort: SignalSort;
  setDirection: (direction: SignalDirectionFilter) => void;
  setTradeStyle: (tradeStyle: SignalTradeStyleFilter) => void;
  setStatus: (status: SignalStatusFilter) => void;
  setPair: (pair: string) => void;
  setSort: (sort: SignalSort) => void;
  reset: () => void;
};

const initialState = {
  direction: "all" as SignalDirectionFilter,
  tradeStyle: "all" as SignalTradeStyleFilter,
  status: "all" as SignalStatusFilter,
  pair: "all",
  sort: "confidence" as SignalSort
};

export const useSignalStore = create<SignalFilterState>((set) => ({
  ...initialState,
  setDirection: (direction) => set({ direction }),
  setTradeStyle: (tradeStyle) => set({ tradeStyle }),
  setStatus: (status) => set({ status }),
  setPair: (pair) => set({ pair }),
  setSort: (sort) => set({ sort }),
  reset: () => set(initialState)
}));
