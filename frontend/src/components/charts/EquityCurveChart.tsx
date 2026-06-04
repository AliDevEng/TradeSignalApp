"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  BaselineSeries,
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp
} from "lightweight-charts";

import { EmptyState } from "@/components/ui/EmptyState";
import type { EquityPoint } from "@/types/performance";

type EquityCurveChartProps = {
  points: EquityPoint[];
};

type ChartPoint = { time: UTCTimestamp; value: number };

/**
 * Map equity points to lightweight-charts data. The library requires strictly
 * ascending, unique time values; close timestamps can collide (two signals
 * resolved in the same second, or mock data sharing a day), so any non-advancing
 * time is nudged forward by a second. That only shifts the x-axis label by
 * seconds — the cumulative-R shape is preserved exactly.
 */
function toChartData(points: EquityPoint[]): ChartPoint[] {
  const data: ChartPoint[] = [];
  let previous = -Infinity;

  for (const point of points) {
    const seconds = Math.floor(new Date(point.closedAt).getTime() / 1000);
    const time = (seconds > previous ? seconds : previous + 1) as UTCTimestamp;
    previous = time;
    data.push({ time, value: point.cumulativeR });
  }

  return data;
}

/**
 * The cumulative-R equity curve, rendered with `lightweight-charts`. A baseline
 * series anchored at 0R paints the curve green while the strategy is net-positive
 * and red while it is underwater. The chart is `autoSize`d (the library owns its
 * own ResizeObserver), so it stays responsive without manual resize wiring.
 */
export function EquityCurveChart({ points }: EquityCurveChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Baseline"> | null>(null);

  const data = useMemo(() => toChartData(points), [points]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#0d131c" },
        textColor: "#9aa4b2",
        fontFamily: "inherit"
      },
      grid: {
        vertLines: { color: "rgba(42,52,69,0.4)" },
        horzLines: { color: "rgba(42,52,69,0.4)" }
      },
      rightPriceScale: { borderColor: "#2a3445" },
      timeScale: { borderColor: "#2a3445", timeVisible: true, secondsVisible: false },
      crosshair: { horzLine: { labelBackgroundColor: "#d8af4f" }, vertLine: { labelBackgroundColor: "#d8af4f" } },
      handleScale: false,
      handleScroll: false
    });

    const series = chart.addSeries(BaselineSeries, {
      baseValue: { type: "price", price: 0 },
      topLineColor: "#7bea9b",
      topFillColor1: "rgba(123,234,155,0.28)",
      topFillColor2: "rgba(123,234,155,0.03)",
      bottomLineColor: "#e5484d",
      bottomFillColor1: "rgba(229,72,77,0.03)",
      bottomFillColor2: "rgba(229,72,77,0.28)",
      lineWidth: 2,
      priceLineVisible: false,
      priceFormat: { type: "custom", formatter: (value: number) => `${value.toFixed(2)}R`, minMove: 0.01 }
    });

    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Push data on every change without tearing down the chart.
  useEffect(() => {
    seriesRef.current?.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  if (points.length === 0) {
    return (
      <EmptyState
        description="The equity curve plots cumulative R as signals close. Once trades resolve, it will chart here."
        title="No closed trades yet"
      />
    );
  }

  return (
    <div
      aria-label="Equity curve: cumulative realised R over closed signals."
      className="h-[360px] w-full overflow-hidden rounded-lg border border-[var(--panel-border)]"
      ref={containerRef}
      role="img"
    />
  );
}
