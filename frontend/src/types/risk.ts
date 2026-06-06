/**
 * UI-facing risk / position-sizing domain types — the parsed mirror of the wire
 * `ApiPositionSize` (see `types/tradeApi.ts`). The backend speaks money as
 * `Decimal` strings; these carry numbers, parsed at the mapping boundary
 * (`lib/riskMappers.ts`) so components format numbers rather than re-parsing.
 */

export type TakeProfitProjection = {
  price: number;
  /** Absolute price distance from entry. */
  distance: number;
  /** Reward:risk ratio against the stop distance. */
  riskReward: number;
  /** Account-currency profit if this take-profit is hit at the sized position. */
  profitAmount: number;
};

export type PositionSize = {
  pair: string;
  quoteCurrency: string;
  contractSize: number;
  minLot: number;
  lotStep: number;
  /** Balance × risk% — the risk the user asked for. */
  requestedRiskAmount: number;
  /** Absolute entry→stop price distance. */
  stopDistance: number;
  /** Lot size, rounded down to the lot step (0 when not affordable at this risk). */
  lots: number;
  /** Base units = lots × contract size. */
  units: number;
  /** Actual loss at the stop for the sized lots (≤ requested). */
  riskAmount: number;
  /** Notional value = units × entry. */
  positionValue: number;
  /** Value of one pip move for the sized position. */
  pipValue: number;
  takeProfits: TakeProfitProjection[];
};

/** Inputs for a single sizing request (UI shape; mapped to the wire body). */
export type PositionSizeRequest = {
  pair: string;
  accountBalance: number;
  riskPercent: number;
  entry: number;
  stopLoss: number;
  takeProfits: number[];
};
