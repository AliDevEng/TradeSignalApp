import { formatIndicator } from "@/lib/formatters";
import type { IndicatorSnapshot } from "@/types/signal";

export type IndicatorTone = "neutral" | "bullish" | "bearish";

export type IndicatorRow = {
  label: string;
  value: string;
  /** Optional short interpretation, e.g. "Overbought". */
  hint?: string;
  tone: IndicatorTone;
};

export type IndicatorGroup = {
  title: string;
  rows: IndicatorRow[];
};

function fmt(value: number | null): string {
  return value === null ? "—" : formatIndicator(value);
}

/** RSI(14) interpretation against the conventional 30/70 bands. */
export function describeRsi(rsi: number | null): { hint?: string; tone: IndicatorTone } {
  if (rsi === null) {
    return { tone: "neutral" };
  }

  if (rsi >= 70) {
    return { hint: "Overbought", tone: "bearish" };
  }

  if (rsi <= 30) {
    return { hint: "Oversold", tone: "bullish" };
  }

  return { hint: "Neutral", tone: "neutral" };
}

function macdTone(histogram: number | null): IndicatorTone {
  if (histogram === null || histogram === 0) {
    return "neutral";
  }

  return histogram > 0 ? "bullish" : "bearish";
}

/** Where price sits relative to an EMA — above is constructive, below is heavy. */
function priceVsLevel(lastClose: number | null, level: number | null): IndicatorTone {
  if (lastClose === null || level === null) {
    return "neutral";
  }

  if (lastClose > level) {
    return "bullish";
  }

  if (lastClose < level) {
    return "bearish";
  }

  return "neutral";
}

/**
 * Group an indicator snapshot into the display sections the detail panel
 * renders. Pure and presentation-agnostic so it can be unit tested in
 * isolation from React.
 */
export function buildIndicatorGroups(snapshot: IndicatorSnapshot): IndicatorGroup[] {
  const rsi = describeRsi(snapshot.rsi14);
  const close = snapshot.lastClose;

  return [
    {
      title: "Momentum",
      rows: [
        { label: "RSI (14)", value: fmt(snapshot.rsi14), hint: rsi.hint, tone: rsi.tone },
        { label: "MACD", value: fmt(snapshot.macd), tone: macdTone(snapshot.macdHistogram) },
        { label: "MACD signal", value: fmt(snapshot.macdSignal), tone: "neutral" },
        {
          label: "MACD histogram",
          value: fmt(snapshot.macdHistogram),
          hint: macdTone(snapshot.macdHistogram) === "bullish" ? "Expanding up" : macdTone(snapshot.macdHistogram) === "bearish" ? "Expanding down" : undefined,
          tone: macdTone(snapshot.macdHistogram)
        }
      ]
    },
    {
      title: "Trend",
      rows: [
        { label: "EMA 20", value: fmt(snapshot.ema20), tone: priceVsLevel(close, snapshot.ema20) },
        { label: "EMA 50", value: fmt(snapshot.ema50), tone: priceVsLevel(close, snapshot.ema50) },
        { label: "EMA 200", value: fmt(snapshot.ema200), tone: priceVsLevel(close, snapshot.ema200) },
        { label: "SMA 20", value: fmt(snapshot.sma20), tone: priceVsLevel(close, snapshot.sma20) },
        { label: "SMA 50", value: fmt(snapshot.sma50), tone: priceVsLevel(close, snapshot.sma50) }
      ]
    },
    {
      title: "Volatility",
      rows: [
        { label: "BB upper", value: fmt(snapshot.bbUpper), tone: "neutral" },
        { label: "BB middle", value: fmt(snapshot.bbMiddle), tone: "neutral" },
        { label: "BB lower", value: fmt(snapshot.bbLower), tone: "neutral" },
        {
          label: "BB %B",
          value: snapshot.bbPercent === null ? "—" : `${(snapshot.bbPercent * 100).toFixed(0)}%`,
          tone: "neutral"
        },
        { label: "ATR (14)", value: fmt(snapshot.atr14), tone: "neutral" }
      ]
    }
  ];
}
