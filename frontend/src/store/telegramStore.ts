import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

/**
 * A small scratchpad for the Telegram connect helper. The *authoritative*
 * credentials live in the backend env (`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`);
 * this only remembers the chat id the user looked up so they can copy it into
 * the deployment config. Persisted to `localStorage`.
 */
type TelegramState = {
  chatId: string;
  setChatId: (chatId: string) => void;
};

export const useTelegramStore = create<TelegramState>()(
  persist(
    (set) => ({
      chatId: "",
      setChatId: (chatId) => set({ chatId })
    }),
    {
      name: "tradesignal-telegram",
      storage: createJSONStorage(() => localStorage),
      skipHydration: true
    }
  )
);
