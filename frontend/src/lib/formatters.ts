export function formatPrice(value: number, precision = 5): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision
  }).format(value);
}

export function formatPercent(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
}

/**
 * Money in the given ISO currency (default USD), e.g. 1234.5 → "$1,234.50".
 * Falls back to a plain 2-decimal number if the currency code is not recognised
 * by the runtime's Intl data.
 */
export function formatCurrency(value: number, currency = "USD"): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  } catch {
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  }
}

export function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1
  }).format(value);
}

export function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    day: "numeric"
  }).format(new Date(value));
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

/**
 * Risk-to-reward ratio for display: at most one decimal, and a whole number
 * when the fraction rounds away. So 2.04 → "2", 2.02 → "2", 2.15 → "2.2",
 * 2.1 → "2.1". Callers append the " : 1" suffix where the layout wants it.
 */
export function formatRiskReward(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  return rounded.toFixed(1).replace(/\.0$/, "");
}

/**
 * Compact "time remaining" label from a millisecond duration, e.g. "12m 30s",
 * "45s", or "1h 5m" for long cadences. Non-positive/invalid input collapses to
 * "any moment now" — the countdown has effectively elapsed.
 */
export function formatCountdown(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) {
    return "any moment now";
  }

  const totalSeconds = Math.ceil(ms / 1_000);
  const hours = Math.floor(totalSeconds / 3_600);
  const minutes = Math.floor((totalSeconds % 3_600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

export function getPricePrecision(symbol: string): number {
  if (symbol.includes("JPY")) {
    return 3;
  }

  if (symbol === "XAUUSD") {
    return 2;
  }

  return 5;
}

/** A signed percentage, e.g. 0.0123 → "+1.23%", -0.04 → "-4.00%". */
export function formatSignedPercent(value: number): string {
  const formatted = new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    signDisplay: "exceptZero"
  }).format(value);

  return formatted;
}

/**
 * Indicator value formatting that scales precision to magnitude: gold-scale
 * numbers get 2 decimals, mid-range (JPY, RSI) get 3, and sub-10 FX values
 * keep 5 so a ~1.08 EMA isn't truncated to 1.084.
 */
export function formatIndicator(value: number): string {
  const magnitude = Math.abs(value);
  const fractionDigits = magnitude >= 1000 ? 2 : magnitude >= 10 ? 3 : 5;

  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits
  }).format(value);
}

const relativeTimeFormatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

const RELATIVE_DIVISIONS: Array<{ amount: number; unit: Intl.RelativeTimeFormatUnit }> = [
  { amount: 60, unit: "second" },
  { amount: 60, unit: "minute" },
  { amount: 24, unit: "hour" },
  { amount: 7, unit: "day" },
  { amount: 4.34524, unit: "week" },
  { amount: 12, unit: "month" },
  { amount: Number.POSITIVE_INFINITY, unit: "year" }
];

/**
 * A human "x ago" / "in x" label relative to `now`. Pure (callers pass `now`)
 * so it is deterministic and trivially testable; the live-ticking variant lives
 * in the `RelativeTime` component.
 */
export function formatRelativeTime(value: string | number | Date, now: number = Date.now()): string {
  const target = value instanceof Date ? value.getTime() : new Date(value).getTime();

  if (!Number.isFinite(target)) {
    return "unknown";
  }

  let duration = (target - now) / 1000;

  for (const division of RELATIVE_DIVISIONS) {
    if (Math.abs(duration) < division.amount) {
      return relativeTimeFormatter.format(Math.round(duration), division.unit);
    }

    duration /= division.amount;
  }

  return relativeTimeFormatter.format(Math.round(duration), "year");
}
