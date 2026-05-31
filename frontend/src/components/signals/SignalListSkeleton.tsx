export function SignalListSkeleton() {
  return (
    <div className="space-y-4" aria-label="Loading signals">
      {Array.from({ length: 3 }).map((_, index) => (
        <div
          className="animate-pulse rounded-lg border border-[var(--panel-border)] bg-[var(--panel)] p-5"
          key={index}
        >
          <div className="flex flex-wrap justify-between gap-4">
            <div className="space-y-3">
              <div className="h-4 w-32 rounded bg-[#263145]" />
              <div className="h-3 w-64 max-w-full rounded bg-[#202a3b]" />
            </div>
            <div className="h-8 w-24 rounded bg-[#263145]" />
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <div className="h-14 rounded bg-[#202a3b]" />
            <div className="h-14 rounded bg-[#202a3b]" />
            <div className="h-14 rounded bg-[#202a3b]" />
          </div>
        </div>
      ))}
    </div>
  );
}
