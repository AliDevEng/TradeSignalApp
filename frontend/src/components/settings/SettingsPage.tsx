"use client";

import { AccountSettingsPanel } from "@/components/settings/AccountSettingsPanel";
import { NotificationSettingsPanel } from "@/components/settings/NotificationSettingsPanel";
import { TelegramConnectPanel } from "@/components/settings/TelegramConnectPanel";

/**
 * Settings surface (Iteration 11): the in-app notification preferences and the
 * Telegram off-platform delivery helper. Both client components — preferences are
 * persisted locally and the Telegram status is read live from `/health`.
 */
export function SettingsPage() {
  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold text-[#fff8df]">Settings</h1>
        <p className="text-sm text-[var(--muted)]">
          Tune what you are notified about in-app, connect off-platform delivery, and set the
          account inputs used to size positions.
        </p>
      </header>
      <div className="grid gap-5 lg:grid-cols-2">
        <NotificationSettingsPanel />
        <TelegramConnectPanel />
        <AccountSettingsPanel />
      </div>
    </div>
  );
}
