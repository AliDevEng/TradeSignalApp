import { HealthPanel } from "@/components/health/HealthPanel";
import { env } from "@/lib/env";

const roadmapItems = [
  { label: "Foundation", status: "Live" },
  { label: "Signal UI", status: "Next" },
  { label: "Charts", status: "Planned" },
  { label: "Delivery", status: "Planned" }
] as const;

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <section className="border-b border-[var(--panel-border)] bg-[var(--panel)]">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-10 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">
              {env.NEXT_PUBLIC_APP_NAME}
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-normal text-[var(--foreground)] sm:text-5xl">
              Trading signal operations dashboard
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-[var(--muted)]">
              Frontend foundation is wired for the FastAPI v1 contract, with typed API access,
              React Query caching, strict TypeScript, and deployment-ready project structure.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[440px]">
            {roadmapItems.map((item) => (
              <div
                className="rounded-lg border border-[var(--panel-border)] bg-[#fafbf7] p-4"
                key={item.label}
              >
                <p className="text-sm font-medium text-[var(--foreground)]">{item.label}</p>
                <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                  {item.status}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] p-6 shadow-sm">
          <h2 className="text-xl font-semibold">System Readiness</h2>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            The first frontend screen validates that the browser can reach the backend health
            endpoint. Signal and pair views can now be added without revisiting provider or API
            plumbing.
          </p>
          <div className="mt-6">
            <HealthPanel />
          </div>
        </div>

        <aside className="rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] p-6 shadow-sm">
          <h2 className="text-xl font-semibold">API Contract</h2>
          <dl className="mt-5 space-y-4 text-sm">
            <div>
              <dt className="font-medium text-[var(--foreground)]">Base URL</dt>
              <dd className="mt-1 break-all text-[var(--muted)]">{env.NEXT_PUBLIC_API_URL}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--foreground)]">Health endpoint</dt>
              <dd className="mt-1 text-[var(--muted)]">GET /health</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--foreground)]">Response strategy</dt>
              <dd className="mt-1 text-[var(--muted)]">
                Direct health responses plus typed v1 success and error envelopes.
              </dd>
            </div>
          </dl>
        </aside>
      </section>
    </main>
  );
}
