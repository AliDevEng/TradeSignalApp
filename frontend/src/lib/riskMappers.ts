import type { ApiPositionSize, ApiTakeProfitProjection } from "@/types/tradeApi";
import type { PositionSize, TakeProfitProjection } from "@/types/risk";

/** Parse a Decimal-string money/quantity field to a finite number (0 on garbage). */
function num(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function mapTakeProfit(api: ApiTakeProfitProjection): TakeProfitProjection {
  return {
    price: num(api.price),
    distance: num(api.distance),
    riskReward: num(api.risk_reward),
    profitAmount: num(api.profit_amount)
  };
}

export function mapApiPositionSize(api: ApiPositionSize): PositionSize {
  return {
    pair: api.pair,
    quoteCurrency: api.quote_currency,
    contractSize: num(api.contract_size),
    minLot: num(api.min_lot),
    lotStep: num(api.lot_step),
    requestedRiskAmount: num(api.requested_risk_amount),
    stopDistance: num(api.stop_distance),
    lots: num(api.lots),
    units: num(api.units),
    riskAmount: num(api.risk_amount),
    positionValue: num(api.position_value),
    pipValue: num(api.pip_value),
    takeProfits: api.take_profits.map(mapTakeProfit)
  };
}
