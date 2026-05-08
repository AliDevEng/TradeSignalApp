import type { Metadata } from "next";

import { AppProviders } from "@/app/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "TradeSignal AI",
  description: "AI-assisted Forex and Gold trade signal dashboard"
};

type RootLayoutProps = Readonly<{
  children: React.ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
