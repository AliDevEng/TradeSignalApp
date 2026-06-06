import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

/**
 * The trader's account inputs for position sizing — balance and the percent of it
 * to risk per trade. Kept entirely client-side (persisted to `localStorage`, no
 * backend account, per the Phase-2 deferral): the position-size endpoint is
 * stateless and these values are sent per request, never stored server-side.
 *
 * `balance === 0` means "not yet configured" — the sizing widgets show a prompt
 * to set it rather than firing a sizing request with no budget.
 */
export type AccountState = {
  balance: number;
  riskPercent: number;
  setAccount: (account: { balance: number; riskPercent: number }) => void;
  clear: () => void;
};

export const DEFAULT_RISK_PERCENT = 1;

export const useAccountStore = create<AccountState>()(
  persist(
    (set) => ({
      balance: 0,
      riskPercent: DEFAULT_RISK_PERCENT,
      setAccount: ({ balance, riskPercent }) => set({ balance, riskPercent }),
      clear: () => set({ balance: 0, riskPercent: DEFAULT_RISK_PERCENT })
    }),
    {
      name: "tradesignal-account",
      storage: createJSONStorage(() => localStorage),
      skipHydration: true
    }
  )
);

/** Whether the account is usable for sizing (a positive balance + risk). */
export function isAccountConfigured(state: Pick<AccountState, "balance" | "riskPercent">): boolean {
  return state.balance > 0 && state.riskPercent > 0;
}
