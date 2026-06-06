"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Wallet } from "lucide-react";
import { z } from "zod";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { zodResolver } from "@/lib/zodResolver";
import { useAccountStore } from "@/store/accountStore";
import { toast } from "@/store/toastStore";

// Inputs arrive as strings from the number fields; `coerce` turns them into the
// numbers the store + sizing endpoint expect, and the bounds mirror the backend
// request schema (positive balance, 0 < risk ≤ 100).
const accountSchema = z.object({
  balance: z.coerce
    .number({ message: "Enter your account balance" })
    .positive("Balance must be greater than 0"),
  riskPercent: z.coerce
    .number({ message: "Enter a risk percent" })
    .gt(0, "Risk must be greater than 0%")
    .max(100, "Risk can’t exceed 100%")
});

type AccountFormValues = z.input<typeof accountSchema>;
type AccountFormOutput = z.output<typeof accountSchema>;

/**
 * Account inputs for position sizing (balance + risk %), validated with
 * react-hook-form + Zod and saved to the persisted {@link useAccountStore}. No
 * account data leaves the browser — sizing is stateless server-side.
 */
export function AccountSettingsPanel() {
  const balance = useAccountStore((state) => state.balance);
  const riskPercent = useAccountStore((state) => state.riskPercent);
  const setAccount = useAccountStore((state) => state.setAccount);
  const clear = useAccountStore((state) => state.clear);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty }
  } = useForm<AccountFormValues, unknown, AccountFormOutput>({
    resolver: zodResolver(accountSchema),
    defaultValues: { balance: balance || "", riskPercent: riskPercent || 1 }
  });

  // Reflect the rehydrated store values once they load in after mount.
  useEffect(() => {
    reset({ balance: balance || "", riskPercent: riskPercent || 1 });
  }, [balance, riskPercent, reset]);

  const onSubmit = handleSubmit((values) => {
    setAccount({ balance: values.balance, riskPercent: values.riskPercent });
    toast({ tone: "success", title: "Account saved", description: "Signals will now show position sizing." });
  });

  return (
    <Card>
      <CardHeader className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Wallet className="h-4 w-4 text-[var(--gold)]" />
          <h2 className="text-sm font-semibold text-[#fff8df]">Account &amp; risk</h2>
        </div>
        {balance > 0 ? (
          <button
            className="text-xs font-semibold text-[var(--blue-strong)] hover:text-[#8ab8ff]"
            onClick={() => {
              clear();
              reset({ balance: "", riskPercent: 1 });
            }}
            type="button"
          >
            Clear
          </button>
        ) : null}
      </CardHeader>
      <CardContent>
        <form className="space-y-4" noValidate onSubmit={onSubmit}>
          <Field
            error={errors.balance?.message}
            hint="Used only to size positions; stored locally, never sent to any account."
            id="account-balance"
            label="Account balance"
          >
            <input
              className="w-full rounded-md border border-[#263247] bg-[#0d131c] px-3 py-2 text-sm text-[#fff8df] outline-none focus:border-[var(--gold)]"
              id="account-balance"
              inputMode="decimal"
              step="any"
              type="number"
              {...register("balance")}
            />
          </Field>

          <Field error={errors.riskPercent?.message} id="account-risk" label="Risk per trade (%)">
            <input
              className="w-full rounded-md border border-[#263247] bg-[#0d131c] px-3 py-2 text-sm text-[#fff8df] outline-none focus:border-[var(--gold)]"
              id="account-risk"
              inputMode="decimal"
              step="any"
              type="number"
              {...register("riskPercent")}
            />
          </Field>

          <button
            className="inline-flex items-center justify-center rounded-md border border-[#8f6a20] bg-[var(--gold)] px-4 py-2 text-sm font-semibold text-[#080a0f] transition-colors hover:bg-[var(--gold-strong)] disabled:opacity-50"
            disabled={!isDirty}
            type="submit"
          >
            Save account
          </button>
        </form>
      </CardContent>
    </Card>
  );
}

function Field({
  children,
  error,
  hint,
  id,
  label
}: {
  children: React.ReactNode;
  error?: string;
  hint?: string;
  id: string;
  label: string;
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-[#fff8df]" htmlFor={id}>
        {label}
      </label>
      <div className="mt-1.5">{children}</div>
      {error ? (
        <p className="mt-1 text-xs text-[#ffb4b4]" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p>
      ) : null}
    </div>
  );
}
