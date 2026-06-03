import "@testing-library/jest-dom/vitest";

import type { AnchorHTMLAttributes, ReactNode } from "react";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Unmount React trees between tests so the DOM and effects don't leak across.
afterEach(() => {
  cleanup();
});

// next/navigation has no router context under jsdom; provide inert defaults so
// components that read it render without a provider. Individual tests can
// override these with vi.mocked(...).mockReturnValue(...).
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn()
  }),
  useSearchParams: () => new URLSearchParams(),
  notFound: vi.fn()
}));

// next/link renders a plain anchor in tests — enough to assert href + content.
// The factory is hoisted above imports, so React is pulled in dynamically.
vi.mock("next/link", async () => {
  const { createElement } = await import("react");

  return {
    default: ({
      children,
      href,
      ...rest
    }: { children: ReactNode; href: string } & AnchorHTMLAttributes<HTMLAnchorElement>) =>
      createElement("a", { href, ...rest }, children)
  };
});
