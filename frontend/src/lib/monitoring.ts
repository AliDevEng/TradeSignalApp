/**
 * Error monitoring seam. Today it logs to the console; in production this is the
 * single place to forward to Sentry/Datadog/etc. without touching call sites.
 * Kept dependency-free and SSR-safe so it can run on the server or the client.
 */

export type ErrorContext = {
  /** Where the error was caught, e.g. "route-error-boundary". */
  source: string;
  /** Next.js error digest, when available. */
  digest?: string;
  [key: string]: unknown;
};

type ErrorReporter = (error: Error, context: ErrorContext) => void;

const consoleReporter: ErrorReporter = (error, context) => {
  console.error(`[monitoring] ${context.source}:`, error, context);
};

let reporter: ErrorReporter = consoleReporter;

/** Swap the reporter at app bootstrap to wire a real provider. */
export function setErrorReporter(next: ErrorReporter): void {
  reporter = next;
}

export function reportError(error: unknown, context: ErrorContext): void {
  const normalized = error instanceof Error ? error : new Error(String(error));

  try {
    reporter(normalized, context);
  } catch {
    // A monitoring failure must never cascade into the UI.
  }
}
