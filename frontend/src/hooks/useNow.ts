"use client";

import { useEffect, useState } from "react";

/**
 * A clock that re-renders the consumer on a fixed interval. Returns `null`
 * until the component has mounted so server and first client render agree
 * (relative-time output is inherently non-deterministic across that boundary).
 */
export function useNow(intervalMs = 1_000): number | null {
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    const tick = () => setNow(Date.now());
    // Defer the first tick out of the effect body (a timer callback, not a
    // synchronous set) so the initial null render still matches the server.
    const initial = window.setTimeout(tick, 0);
    const interval = window.setInterval(tick, intervalMs);

    return () => {
      window.clearTimeout(initial);
      window.clearInterval(interval);
    };
  }, [intervalMs]);

  return now;
}
