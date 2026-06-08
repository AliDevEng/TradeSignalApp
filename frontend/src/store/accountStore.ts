import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

/**
 * The trader's account inputs for position sizing — balance, the percent of it
 * to risk per trade, and a daily-risk ceiling used by the open-risk meter. Kept
 * entirely client-side (persisted to `localStorage`, no backend account, per the
 * Phase-2 deferral): the position-size endpoint is stateless and these values are
 * sent per request, never stored server-side.
 *
 * `balance === 0` means "not yet configured" — the sizing widgets show a prompt
 * to set it rather than firing a sizing request with no budget.
 */
export type AccountState = {
  balance: number;
  riskPercent: number;
  /**
   * Soft ceiling on total open risk, as a percent of balance. Drives the
   * open-risk meter's warning band; it does not block sizing. The classic
   * prop-firm convention is ~5%.
   */
  dailyRiskCapPercent: number;
  setAccount: (account: { balance: number; riskPercent: number }) => void;
  /** Live single-field setters so inline editors (the bar pill) can write on change. */
  setBalance: (balance: number) => void;
  setRiskPercent: (riskPercent: number) => void;
  setDailyRiskCapPercent: (dailyRiskCapPercent: number) => void;
  clear: () => void;
};

export const DEFAULT_RISK_PERCENT = 1;
export const DEFAULT_DAILY_RISK_CAP_PERCENT = 5;

export const useAccountStore = create<AccountState>()(
  persist(
    (set) => ({
      balance: 0,
      riskPercent: DEFAULT_RISK_PERCENT,
      dailyRiskCapPercent: DEFAULT_DAILY_RISK_CAP_PERCENT,
      setAccount: ({ balance, riskPercent }) => set({ balance, riskPercent }),
      setBalance: (balance) => set({ balance }),
      setRiskPercent: (riskPercent) => set({ riskPercent }),
      setDailyRiskCapPercent: (dailyRiskCapPercent) => set({ dailyRiskCapPercent }),
      clear: () =>
        set({
          balance: 0,
          riskPercent: DEFAULT_RISK_PERCENT,
          dailyRiskCapPercent: DEFAULT_DAILY_RISK_CAP_PERCENT
        })
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
