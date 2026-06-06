"use client";

import { useEffect } from "react";

import { useAccountStore } from "@/store/accountStore";
import { useNotificationPrefsStore } from "@/store/notificationPrefsStore";
import { useNotificationStore } from "@/store/notificationStore";
import { useTelegramStore } from "@/store/telegramStore";
import { useUIStore } from "@/store/uiStore";

/**
 * Rehydrates the persisted Zustand stores on the client after mount. The stores
 * use `skipHydration` so server and first client render share default state;
 * this restores the user's saved preferences once hydration is safe.
 */
export function StoreHydration() {
  useEffect(() => {
    void useUIStore.persist.rehydrate();
    void useNotificationStore.persist.rehydrate();
    void useNotificationPrefsStore.persist.rehydrate();
    void useTelegramStore.persist.rehydrate();
    void useAccountStore.persist.rehydrate();
  }, []);

  return null;
}
