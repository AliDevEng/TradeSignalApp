"use client";

import { useEffect } from "react";

import { reportError } from "@/lib/monitoring";
import "./globals.css";

type GlobalErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

/**
 * Last-resort boundary for errors thrown in the root layout itself. It replaces
 * the entire document, so it must render its own <html>/<body> and cannot rely
 * on the app shell or design tokens being mounted.
 */
export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    reportError(error, { source: "global-error-boundary", digest: error.digest });
  }, [error]);

  return (
    <html lang="en">
      <body style={{ background: "#090b10", color: "#f6f0df", fontFamily: "system-ui, sans-serif" }}>
        <main
          style={{
            minHeight: "100dvh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "1rem",
            padding: "2rem",
            textAlign: "center"
          }}
        >
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600 }}>Something went wrong</h1>
          <p style={{ maxWidth: "32rem", lineHeight: 1.6, color: "#9aa4b2" }}>
            An unexpected error interrupted the app. The issue has been logged.
          </p>
          <button
            onClick={reset}
            style={{
              border: "1px solid #8f6a20",
              background: "#d8af4f",
              color: "#0a0c10",
              fontWeight: 600,
              borderRadius: "0.5rem",
              padding: "0.5rem 1rem",
              cursor: "pointer"
            }}
            type="button"
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
