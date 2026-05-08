import { BrainCircuit, CircleAlert, ListChecks, ShieldCheck } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import type { SignalReasoning } from "@/types/signal";

type ReasoningPanelProps = {
  reasoning: SignalReasoning;
};

export function ReasoningPanel({ reasoning }: ReasoningPanelProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <BrainCircuit className="h-4 w-4 text-[var(--gold)]" />
          <h2 className="text-lg font-semibold text-[#fff8df]">Reasoning Panel</h2>
        </div>
      </CardHeader>
      <CardContent className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          <section>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
              Thesis
            </h3>
            <p className="mt-3 text-sm leading-7 text-[#c2cad6]">{reasoning.thesis}</p>
          </section>

          <section>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
              Confirmations
            </h3>
            <div className="mt-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
              <ListChecks className="h-4 w-4 text-[var(--blue-strong)]" />
              Signal evidence
            </div>
            <ul className="mt-3 space-y-3 text-sm leading-7 text-[#c2cad6]">
              {reasoning.confirmations.map((item) => (
                <li
                  className="rounded-lg border border-[var(--panel-border)] bg-[#0d131c] px-4 py-3"
                  key={item}
                >
                  {item}
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border border-[#6f5620] bg-[#120f09] p-4">
            <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
              <ShieldCheck className="h-4 w-4 text-[var(--gold-strong)]" />
              Risk Plan
            </div>
            <p className="mt-3 text-sm leading-7 text-[#c7b98d]">{reasoning.riskPlan}</p>
          </div>

          <div className="rounded-lg border border-[#6e2029] bg-[var(--red-soft)] p-4">
            <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
              <CircleAlert className="h-4 w-4 text-[var(--red-strong)]" />
              Invalidation
            </div>
            <p className="mt-3 text-sm leading-7 text-[#f0c8ca]">{reasoning.invalidation}</p>
          </div>

          <section>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
              Execution Notes
            </h3>
            <div className="mt-3 grid gap-3">
              {reasoning.executionNotes.map((item) => (
                <div
                  className="rounded-lg border border-[var(--panel-border)] bg-[#101722] px-4 py-3 text-sm leading-7 text-[#c2cad6]"
                  key={item}
                >
                  {item}
                </div>
              ))}
            </div>
          </section>
        </div>
      </CardContent>
    </Card>
  );
}
