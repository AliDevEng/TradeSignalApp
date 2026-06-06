import { beforeEach, describe, expect, it } from "vitest";

import {
  DEFAULT_RISK_PERCENT,
  isAccountConfigured,
  useAccountStore
} from "@/store/accountStore";

describe("accountStore", () => {
  beforeEach(() => {
    useAccountStore.getState().clear();
    localStorage.clear();
  });

  it("starts unconfigured with a zero balance and the default risk", () => {
    const state = useAccountStore.getState();
    expect(state.balance).toBe(0);
    expect(state.riskPercent).toBe(DEFAULT_RISK_PERCENT);
    expect(isAccountConfigured(state)).toBe(false);
  });

  it("saves balance + risk and becomes configured", () => {
    useAccountStore.getState().setAccount({ balance: 10000, riskPercent: 2 });

    const state = useAccountStore.getState();
    expect(state.balance).toBe(10000);
    expect(state.riskPercent).toBe(2);
    expect(isAccountConfigured(state)).toBe(true);
  });

  it("persists the saved account to localStorage", () => {
    useAccountStore.getState().setAccount({ balance: 5000, riskPercent: 1.5 });

    const raw = localStorage.getItem("tradesignal-account");
    expect(raw).toContain("5000");
    expect(raw).toContain("1.5");
  });

  it("clear() resets to the unconfigured default", () => {
    useAccountStore.getState().setAccount({ balance: 10000, riskPercent: 3 });
    useAccountStore.getState().clear();

    const state = useAccountStore.getState();
    expect(state.balance).toBe(0);
    expect(state.riskPercent).toBe(DEFAULT_RISK_PERCENT);
    expect(isAccountConfigured(state)).toBe(false);
  });

  it("treats a non-positive balance or risk as unconfigured", () => {
    expect(isAccountConfigured({ balance: 0, riskPercent: 1 })).toBe(false);
    expect(isAccountConfigured({ balance: 100, riskPercent: 0 })).toBe(false);
  });
});
