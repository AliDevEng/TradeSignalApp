"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { env, STREAM_ENABLED } from "@/lib/env";
import { notificationForEvent, parseStreamEvent, queryKeysToInvalidate } from "@/lib/stream";
import { track } from "@/lib/analytics";
import { useNotificationStore } from "@/store/notificationStore";
import { toast } from "@/store/toastStore";
import { STREAM_EVENT_TYPES, type StreamStatus } from "@/types/stream";

/**
 * Subscribe to the backend SSE stream for real-time updates. On each event it
 * invalidates the affected React-Query caches (so the UI refetches instantly)
 * and, for signal events, raises a toast + a persistent notification — deduped
 * against the polling notifier so nothing is announced twice.
 *
 * The browser's `EventSource` reconnects automatically (and resumes via
 * `Last-Event-ID`), so this hook only mirrors the connection state for the
 * live indicator; it does not implement its own retry loop. Returns the current
 * {@link StreamStatus}.
 */
export function useEventStream(): StreamStatus {
  const queryClient = useQueryClient();
  const pushLiveNotification = useNotificationStore((state) => state.pushLiveNotification);
  const [status, setStatus] = useState<StreamStatus>(STREAM_ENABLED ? "connecting" : "offline");

  useEffect(() => {
    if (!STREAM_ENABLED || typeof window === "undefined" || typeof EventSource === "undefined") {
      return;
    }

    let cancelled = false;
    let source: EventSource;
    try {
      source = new EventSource(`${env.NEXT_PUBLIC_API_URL}/stream`);
    } catch {
      // Constructing EventSource essentially never throws for a valid URL; if it
      // does, report offline on the next tick (a synchronous setState inside an
      // effect body triggers cascading renders and is disallowed).
      queueMicrotask(() => {
        if (!cancelled) {
          setStatus("offline");
        }
      });
      return;
    }

    const onOpen = () => {
      if (!cancelled) {
        setStatus("live");
      }
    };
    // EventSource transitions to CONNECTING and retries on its own; surface that
    // as "offline" until the next open rather than treating it as fatal.
    const onError = () => {
      if (!cancelled) {
        setStatus("offline");
      }
    };

    const onEvent = (raw: MessageEvent) => {
      const event = parseStreamEvent(raw.data);
      if (!event) {
        return;
      }
      for (const queryKey of queryKeysToInvalidate(event.type)) {
        void queryClient.invalidateQueries({ queryKey });
      }
      const mapped = notificationForEvent(event);
      if (!mapped) {
        return;
      }
      const added = pushLiveNotification(mapped.notification, mapped.markSeenSignalId);
      if (added) {
        track({ name: "signal_notification", count: 1 });
        toast({
          tone: mapped.tone,
          title: mapped.notification.title,
          description: mapped.notification.description,
          href: mapped.notification.href
        });
      }
    };

    source.addEventListener("open", onOpen);
    source.addEventListener("error", onError);
    for (const type of STREAM_EVENT_TYPES) {
      source.addEventListener(type, onEvent);
    }

    return () => {
      cancelled = true;
      source.close();
    };
  }, [queryClient, pushLiveNotification]);

  return status;
}
