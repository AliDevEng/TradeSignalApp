import type { Metadata } from "next";

import { AppProviders } from "@/app/providers";
import { AppShell } from "@/components/layout/AppShell";
import { env } from "@/lib/env";
import "./globals.css";

const description =
  "AI-assisted Forex and Gold trade signals with entry, stop-loss, and a TP1–TP3 take-profit ladder, technical-indicator context, and live analysis-run observability.";

export const metadata: Metadata = {
  metadataBase: new URL(env.NEXT_PUBLIC_SITE_URL),
  title: {
    default: `${env.NEXT_PUBLIC_APP_NAME} — AI market command`,
    template: `%s · ${env.NEXT_PUBLIC_APP_NAME}`
  },
  description,
  applicationName: env.NEXT_PUBLIC_APP_NAME,
  keywords: ["forex signals", "XAUUSD", "gold trading", "trade signals", "technical analysis", "AI trading"],
  authors: [{ name: env.NEXT_PUBLIC_APP_NAME }],
  openGraph: {
    type: "website",
    siteName: env.NEXT_PUBLIC_APP_NAME,
    title: `${env.NEXT_PUBLIC_APP_NAME} — AI market command`,
    description,
    url: "/"
  },
  twitter: {
    card: "summary_large_image",
    title: `${env.NEXT_PUBLIC_APP_NAME} — AI market command`,
    description
  },
  robots: { index: true, follow: true }
};

type RootLayoutProps = Readonly<{
  children: React.ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>
        <AppProviders>
          <AppShell>{children}</AppShell>
        </AppProviders>
      </body>
    </html>
  );
}
