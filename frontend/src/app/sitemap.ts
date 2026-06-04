import type { MetadataRoute } from "next";

import { env } from "@/lib/env";

/**
 * Static, always-available routes. Dynamic detail routes (`/pairs/[symbol]`,
 * `/signals/[id]`, `/analysis/[runId]`) are intentionally omitted — they depend
 * on live backend data and are reached via in-app navigation, not crawled.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const base = env.NEXT_PUBLIC_SITE_URL;
  const lastModified = new Date();

  return [
    { url: `${base}/`, lastModified, changeFrequency: "hourly", priority: 1 },
    { url: `${base}/dashboard`, lastModified, changeFrequency: "hourly", priority: 0.9 },
    { url: `${base}/signals`, lastModified, changeFrequency: "hourly", priority: 0.8 },
    { url: `${base}/closed`, lastModified, changeFrequency: "hourly", priority: 0.7 },
    { url: `${base}/performance`, lastModified, changeFrequency: "hourly", priority: 0.7 },
    { url: `${base}/analysis`, lastModified, changeFrequency: "hourly", priority: 0.6 }
  ];
}
