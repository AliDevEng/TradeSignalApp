import { z } from "zod";

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().default("http://localhost:8000/api/v1"),
  NEXT_PUBLIC_APP_NAME: z.string().min(1).default("TradeSignal AI"),
  // Canonical site origin used for metadata (OG/canonical), robots, and sitemap.
  NEXT_PUBLIC_SITE_URL: z.string().url().default("http://localhost:3000")
});

export const env = envSchema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
  NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL
});
