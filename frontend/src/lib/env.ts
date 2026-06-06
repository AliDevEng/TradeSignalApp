import { z } from "zod";

/**
 * Public runtime configuration. Every field is resilient: a malformed
 * `NEXT_PUBLIC_*` value falls back to its default via `.catch(...)` rather than
 * throwing at import time, which would white-screen the whole client bundle
 * (this module is imported in the root layout). A bad value degrades to the
 * default instead of taking the app down.
 */
const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().catch("http://localhost:8000/api/v1"),
  NEXT_PUBLIC_APP_NAME: z.string().min(1).catch("TradeSignal AI"),
  // Canonical site origin used for metadata (OG/canonical), robots, and sitemap.
  NEXT_PUBLIC_SITE_URL: z.string().url().catch("http://localhost:3000"),
  // When true, the UI may show bundled sample data if the live API is
  // unreachable. Default OFF so production never presents fabricated trade
  // signals as if they were live (see the preview helpers). Accepts "true"/"1".
  NEXT_PUBLIC_PREVIEW_DATA: z
    .preprocess((value) => value === true || value === "true" || value === "1", z.boolean())
    .catch(false),
  // Real-time updates via the backend SSE stream (GET /api/v1/stream). On by
  // default; set to "false"/"0" to fall back to polling only (e.g. behind a proxy
  // that buffers event streams). Accepts "true"/"1"/"false"/"0".
  NEXT_PUBLIC_STREAM_ENABLED: z
    .preprocess(
      (value) => !(value === false || value === "false" || value === "0"),
      z.boolean()
    )
    .catch(true)
});

export const env = envSchema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
  NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL,
  NEXT_PUBLIC_PREVIEW_DATA: process.env.NEXT_PUBLIC_PREVIEW_DATA,
  NEXT_PUBLIC_STREAM_ENABLED: process.env.NEXT_PUBLIC_STREAM_ENABLED
});

/**
 * Whether the UI is allowed to fall back to bundled sample data when the live
 * API is unavailable. Off by default — a financial UI must not render fabricated
 * trade levels indistinguishably from live ones.
 */
export const PREVIEW_DATA_ENABLED = env.NEXT_PUBLIC_PREVIEW_DATA;

/** Whether the client should open the live SSE stream for real-time updates. */
export const STREAM_ENABLED = env.NEXT_PUBLIC_STREAM_ENABLED;
