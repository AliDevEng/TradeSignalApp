import type {
  ApiCalibrationBucket,
  ApiEquityPoint,
  ApiPerformance,
  ApiPerformanceSummary
} from "@/types/tradeApi";
import type {
  CalibrationBucket,
  EquityPoint,
  Performance,
  PerformanceSummary
} from "@/types/performance";

/** Parse a Decimal-string money/R field to a finite number (0 on garbage). */
function num(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function mapSummary(api: ApiPerformanceSummary): PerformanceSummary {
  return {
    total: api.total,
    wins: api.wins,
    losses: api.losses,
    winRate: api.win_rate,
    totalR: num(api.total_r),
    avgR: num(api.avg_r),
    // Preserve the explicit null (no losing R) rather than coercing it to 0.
    profitFactor: api.profit_factor,
    grossProfit: num(api.gross_profit),
    grossLoss: num(api.gross_loss)
  };
}

function mapBucket(api: ApiCalibrationBucket): CalibrationBucket {
  return {
    label: api.label,
    lower: api.lower,
    upper: api.upper,
    count: api.count,
    avgConfidence: api.avg_confidence,
    winRate: api.win_rate,
    wins: api.wins
  };
}

function mapEquityPoint(api: ApiEquityPoint): EquityPoint {
  return {
    signalId: api.signal_id,
    closedAt: api.closed_at,
    realizedR: num(api.realized_r),
    cumulativeR: num(api.cumulative_r)
  };
}

export function mapApiPerformance(api: ApiPerformance): Performance {
  return {
    overall: mapSummary(api.overall),
    byType: {
      scalp: mapSummary(api.by_type.scalp),
      swing: mapSummary(api.by_type.swing)
    },
    calibration: api.calibration.map(mapBucket),
    equityCurve: api.equity_curve.map(mapEquityPoint),
    generatedAt: api.generated_at
  };
}
