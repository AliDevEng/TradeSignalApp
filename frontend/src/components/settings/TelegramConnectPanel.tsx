"use client";

import { useState } from "react";
import { Check, Copy, ExternalLink, Send } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { useHealthQuery } from "@/hooks/useHealthQuery";
import { describeNotificationStatus, type NotificationConnectionTone } from "@/lib/notifications";
import { useTelegramStore } from "@/store/telegramStore";

const TONE_DOT: Record<NotificationConnectionTone, string> = {
  connected: "bg-[var(--green,#3fb950)]",
  disabled: "bg-[#566174]",
  down: "bg-[var(--red,#e5534b)]",
  unknown: "bg-[#566174]"
};

/** Telegram bot to message for chat-id discovery. */
const CHAT_ID_BOT_URL = "https://t.me/userinfobot";

/**
 * Telegram connect helper: surfaces the live connection status (from the backend
 * `/health` `notifications` component), links the bot used to discover a chat id,
 * and remembers the chat id the user looked up so it can be copied into the
 * backend env. Delivery itself is configured server-side, by design.
 */
export function TelegramConnectPanel() {
  const health = useHealthQuery();
  const chatId = useTelegramStore((s) => s.chatId);
  const setChatId = useTelegramStore((s) => s.setChatId);
  const [copied, setCopied] = useState(false);

  const view = describeNotificationStatus(health.data?.components.notifications);

  async function copyChatId() {
    if (!chatId || typeof navigator === "undefined" || !navigator.clipboard) {
      return;
    }
    try {
      await navigator.clipboard.writeText(chatId);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be blocked by permissions; silently no-op.
    }
  }

  return (
    <Card>
      <CardHeader className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Send className="h-4 w-4 text-[var(--blue-strong)]" />
          <h2 className="text-sm font-semibold text-[#fff8df]">Telegram delivery</h2>
        </div>
        <span
          className="inline-flex items-center gap-1.5 rounded-md border border-[#293244] bg-[#101722] px-2 py-1 text-xs font-semibold text-[#9aa4b2]"
          role="status"
        >
          <span aria-hidden className={`h-2 w-2 rounded-full ${TONE_DOT[view.tone]}`} />
          {health.isLoading ? "Checking…" : view.label}
        </span>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-[var(--muted)]">{view.hint}</p>

        <ol className="space-y-3 text-sm text-[#cdd6e3]">
          <li className="flex flex-col gap-1">
            <span className="font-semibold text-[#fff8df]">1. Find your chat id</span>
            <a
              className="inline-flex w-fit items-center gap-1.5 text-xs font-semibold text-[var(--blue-strong)] hover:text-[#8ab8ff]"
              href={CHAT_ID_BOT_URL}
              rel="noreferrer noopener"
              target="_blank"
            >
              Open @userinfobot <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </li>
          <li className="flex flex-col gap-1">
            <span className="font-semibold text-[#fff8df]">2. Save it</span>
            <div className="flex gap-2">
              <input
                aria-label="Telegram chat id"
                className="min-w-0 flex-1 rounded-md border border-[#263247] bg-[#0d131c] px-3 py-2 text-sm text-[#fff8df] outline-none focus:border-[var(--gold)]"
                inputMode="numeric"
                onChange={(event) => setChatId(event.target.value.trim())}
                placeholder="e.g. 123456789"
                value={chatId}
              />
              <button
                aria-label="Copy chat id"
                className="inline-flex items-center gap-1.5 rounded-md border border-[#263247] bg-[#101722] px-3 text-xs font-semibold text-[#a5afbf] transition-colors hover:text-[#fff8df] disabled:opacity-40"
                disabled={!chatId}
                onClick={copyChatId}
                type="button"
              >
                {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
          </li>
          <li className="flex flex-col gap-1">
            <span className="font-semibold text-[#fff8df]">3. Configure the backend</span>
            <span className="text-xs text-[var(--muted)]">
              Set <code className="text-[var(--gold-strong)]">NOTIFICATIONS_ENABLED=true</code>,{" "}
              <code className="text-[var(--gold-strong)]">TELEGRAM_BOT_TOKEN</code> and{" "}
              <code className="text-[var(--gold-strong)]">TELEGRAM_CHAT_ID</code> in the backend
              environment, then restart. Status above turns green once the dispatcher is running.
            </span>
          </li>
        </ol>
      </CardContent>
    </Card>
  );
}
