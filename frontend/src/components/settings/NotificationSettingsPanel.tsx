"use client";

import { BellOff, BellRing } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import type { SignalTradeStyle } from "@/types/signal";
import { useNotificationPrefsStore } from "@/store/notificationPrefsStore";

const STYLE_OPTIONS: ReadonlyArray<{ value: SignalTradeStyle; label: string }> = [
  { value: "scalp", label: "Scalp" },
  { value: "swing", label: "Swing" }
];

function Toggle({
  checked,
  onChange,
  label,
  description
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 py-2">
      <span className="min-w-0">
        <span className="block text-sm font-semibold text-[#fff8df]">{label}</span>
        {description ? (
          <span className="mt-0.5 block text-xs text-[var(--muted)]">{description}</span>
        ) : null}
      </span>
      <button
        aria-checked={checked}
        aria-label={label}
        className={`relative mt-0.5 inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors ${
          checked ? "bg-[var(--gold)]" : "bg-[#2a3346]"
        }`}
        onClick={() => onChange(!checked)}
        role="switch"
        type="button"
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-[#080a0f] transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </button>
    </label>
  );
}

/**
 * The in-app notification preferences panel — a client-side surfacing policy
 * mirroring the backend's server-side `NotificationPreferences`. It governs which
 * live-stream events raise a toast + feed entry in this browser (cache refresh is
 * unaffected, so views stay live regardless). Persisted to `localStorage`.
 */
export function NotificationSettingsPanel() {
  const enabled = useNotificationPrefsStore((s) => s.enabled);
  const minConfidence = useNotificationPrefsStore((s) => s.minConfidence);
  const styles = useNotificationPrefsStore((s) => s.styles);
  const onlyActionable = useNotificationPrefsStore((s) => s.onlyActionable);
  const onSignalCreated = useNotificationPrefsStore((s) => s.onSignalCreated);
  const onSignalClosed = useNotificationPrefsStore((s) => s.onSignalClosed);

  const setEnabled = useNotificationPrefsStore((s) => s.setEnabled);
  const setMinConfidence = useNotificationPrefsStore((s) => s.setMinConfidence);
  const toggleStyle = useNotificationPrefsStore((s) => s.toggleStyle);
  const setOnlyActionable = useNotificationPrefsStore((s) => s.setOnlyActionable);
  const setOnSignalCreated = useNotificationPrefsStore((s) => s.setOnSignalCreated);
  const setOnSignalClosed = useNotificationPrefsStore((s) => s.setOnSignalClosed);
  const reset = useNotificationPrefsStore((s) => s.reset);

  const confidencePct = Math.round(minConfidence * 100);

  return (
    <Card>
      <CardHeader className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {enabled ? (
            <BellRing className="h-4 w-4 text-[var(--gold)]" />
          ) : (
            <BellOff className="h-4 w-4 text-[var(--muted)]" />
          )}
          <h2 className="text-sm font-semibold text-[#fff8df]">In-app notifications</h2>
        </div>
        <button
          className="text-xs font-semibold text-[var(--blue-strong)] hover:text-[#8ab8ff]"
          onClick={reset}
          type="button"
        >
          Reset
        </button>
      </CardHeader>
      <CardContent className="space-y-1">
        <Toggle
          checked={enabled}
          label="Enable notifications"
          description="Master switch for toasts + the bell feed from live events. Views still refresh when off."
          onChange={setEnabled}
        />

        <fieldset
          className={enabled ? "space-y-1" : "pointer-events-none space-y-1 opacity-50"}
          disabled={!enabled}
        >
          <div className="border-t border-[var(--panel-border)] pt-3">
            <label className="flex items-center justify-between text-sm font-semibold text-[#fff8df]">
              Minimum confidence
              <span className="tabular-nums text-[var(--gold-strong)]">{confidencePct}%</span>
            </label>
            <input
              aria-label="Minimum confidence"
              className="mt-2 w-full accent-[var(--gold)]"
              max={100}
              min={0}
              onChange={(event) => setMinConfidence(Number(event.target.value) / 100)}
              step={5}
              type="range"
              value={confidencePct}
            />
            <p className="mt-1 text-xs text-[var(--muted)]">
              Only new signals at or above this confidence raise a notification.
            </p>
          </div>

          <div className="border-t border-[var(--panel-border)] pt-3">
            <p className="text-sm font-semibold text-[#fff8df]">Styles</p>
            <div className="mt-2 flex gap-2">
              {STYLE_OPTIONS.map((option) => {
                const active = styles.includes(option.value);
                return (
                  <button
                    aria-pressed={active}
                    className={`rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors ${
                      active
                        ? "border-[#8f6a20] bg-[var(--gold)] text-[#080a0f]"
                        : "border-[#263247] bg-[#101722] text-[#a5afbf] hover:text-[#fff8df]"
                    }`}
                    key={option.value}
                    onClick={() => toggleStyle(option.value)}
                    type="button"
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
            <p className="mt-1 text-xs text-[var(--muted)]">
              Deselect a style to mute it. With none selected, all styles notify.
            </p>
          </div>

          <div className="border-t border-[var(--panel-border)] pt-1">
            <Toggle
              checked={onlyActionable}
              label="Actionable only"
              description="Skip bias-only signals the quality gate marks not tradeable."
              onChange={setOnlyActionable}
            />
            <Toggle
              checked={onSignalCreated}
              label="New signals"
              onChange={setOnSignalCreated}
            />
            <Toggle
              checked={onSignalClosed}
              label="Signal closes (TP / SL hit)"
              onChange={setOnSignalClosed}
            />
          </div>
        </fieldset>
      </CardContent>
    </Card>
  );
}
