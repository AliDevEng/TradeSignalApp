import type { Metadata } from "next";

import { SettingsPage } from "@/components/settings/SettingsPage";

export const metadata: Metadata = {
  title: "Settings",
  description:
    "Notification preferences and off-platform delivery: choose which live signals raise in-app alerts and connect Telegram for push notifications."
};

export default function Settings() {
  return <SettingsPage />;
}
