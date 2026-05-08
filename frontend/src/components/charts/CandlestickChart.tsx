"use client";

import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  LineStyle,
  createChart,
  type CandlestickData,
  type IChartApi,
  type PriceLineOptions,
  type Time,
  type UTCTimestamp
} from "lightweight-charts";

import { SignalOverlay } from "@/components/charts/SignalOverlay";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { formatTime } from "@/lib/formatters";
import { getSignalPriceLevels } from "@/lib/trading";
import type { PriceCandle, Signal } from "@/types/signal";

type CandlestickChartProps = {
  candles: PriceCandle[];
  signal?: Signal;
  title: string;
  subtitle: string;
};

const overlayLineStyles = {
  entry: { color: "#d8af4f", lineStyle: LineStyle.Solid },
  stop: { color: "#e5484d", lineStyle: LineStyle.Dashed },
  target: { color: "#2f81f7", lineStyle: LineStyle.Dashed }
} as const;

function toChartTime(value: string): UTCTimestamp {
  return Math.floor(new Date(value).getTime() / 1000) as UTCTimestamp;
}

function toSeriesData(candles: PriceCandle[]): CandlestickData<Time>[] {
  return candles.map((candle) => ({
    time: toChartTime(candle.time),
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close
  }));
}

type CandlestickSeriesApi = ReturnType<IChartApi["addSeries"]>;

function createOverlayLines(series: CandlestickSeriesApi, signal: Signal): () => void {
  const priceLines = getSignalPriceLevels(signal).map((level) =>
    series.createPriceLine({
      axisLabelVisible: true,
      axisLabelColor: overlayLineStyles[level.tone].color,
      axisLabelTextColor: "#090b10",
      color: overlayLineStyles[level.tone].color,
      lineVisible: true,
      lineStyle: overlayLineStyles[level.tone].lineStyle,
      lineWidth: level.tone === "entry" ? 2 : 1,
      price: level.price,
      title: level.label
    } satisfies PriceLineOptions)
  );

  return () => {
    priceLines.forEach((line) => {
      series.removePriceLine(line);
    });
  };
}

export function CandlestickChart({
  candles,
  signal,
  title,
  subtitle
}: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || candles.length === 0) {
      return undefined;
    }

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#0d131c" },
        textColor: "#9aa4b2"
      },
      grid: {
        vertLines: { color: "rgba(42, 52, 69, 0.6)" },
        horzLines: { color: "rgba(42, 52, 69, 0.6)" }
      },
      crosshair: {
        vertLine: {
          color: "rgba(216, 175, 79, 0.35)",
          labelBackgroundColor: "#151006"
        },
        horzLine: {
          color: "rgba(88, 166, 255, 0.35)",
          labelBackgroundColor: "#10243d"
        }
      },
      rightPriceScale: {
        borderColor: "#2a3445"
      },
      timeScale: {
        borderColor: "#2a3445",
        timeVisible: true
      }
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#d8af4f",
      downColor: "#e5484d",
      borderVisible: false,
      wickUpColor: "#f2c96b",
      wickDownColor: "#ff6b70"
    });

    series.setData(toSeriesData(candles));
    chart.timeScale().fitContent();

    let cleanupOverlay: () => void = () => {};
    if (signal) {
      cleanupOverlay = createOverlayLines(series, signal);
    }

    const resizeObserver = new ResizeObserver(() => {
      chart.timeScale().fitContent();
    });
    resizeObserver.observe(container);

    chartRef.current = chart;

    return () => {
      cleanupOverlay();
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [candles, signal]);

  const latestCandle = candles.at(-1);

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-[#fff8df]">{title}</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">{subtitle}</p>
          </div>
          {latestCandle ? (
            <p className="text-xs font-medium text-[var(--muted)]">
              Latest candle {formatTime(latestCandle.time)}
            </p>
          ) : null}
        </div>
        {signal ? <SignalOverlay signal={signal} /> : null}
      </CardHeader>
      <CardContent className="space-y-4">
        {candles.length > 0 ? (
          <div className="h-[420px] w-full overflow-hidden rounded-lg border border-[var(--panel-border)] bg-[#0d131c]">
            <div className="h-full w-full" ref={containerRef} />
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-[#45536a] bg-[#0d131c] p-10 text-center text-sm text-[var(--muted)]">
            No chart data is available for this pair yet.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
