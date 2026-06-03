"use client";

import { create } from "zustand";

export type ToastTone = "info" | "success" | "danger";

export type Toast = {
  id: string;
  title: string;
  description?: string;
  tone: ToastTone;
  /** Optional deep link rendered as an action on the toast. */
  href?: string;
};

type ToastInput = Omit<Toast, "id"> & { durationMs?: number };

type ToastState = {
  toasts: Toast[];
  addToast: (toast: ToastInput) => string;
  dismissToast: (id: string) => void;
};

const DEFAULT_DURATION_MS = 5_000;

function createId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  addToast: ({ durationMs = DEFAULT_DURATION_MS, ...toast }) => {
    const id = createId();
    set((state) => ({ toasts: [...state.toasts, { ...toast, id }] }));

    if (durationMs > 0 && typeof window !== "undefined") {
      window.setTimeout(() => get().dismissToast(id), durationMs);
    }

    return id;
  },
  dismissToast: (id) => set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) }))
}));

/** Imperative helper for non-component callers (e.g. mutation handlers). */
export const toast = (input: ToastInput): string => useToastStore.getState().addToast(input);
