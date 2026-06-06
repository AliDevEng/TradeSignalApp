import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

/**
 * Render a component tree inside a fresh React Query client — for components that
 * (directly or via a child) call a query hook. Retries are off so a queryless
 * jsdom render settles immediately. Mirrors RTL's `render` return (incl.
 * `rerender`, which re-applies this wrapper).
 */
export function renderWithClient(ui: ReactElement, options?: Omit<RenderOptions, "wrapper">) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }

  return render(ui, { wrapper: Wrapper, ...options });
}
