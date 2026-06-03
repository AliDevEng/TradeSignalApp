# Frontend Setup - TradeSignal AI

## Goal
Create a modern Next.js, React, TypeScript frontend with production-grade foundations for dashboards, charts, forms, state, and API integrations.

## Installed Versions
Verified on 2026-05-08:

- `next`: `16.2.6`
- `react`: `19.2.6`
- `react-dom`: `19.2.6`
- `typescript`: `6.0.3`
- `tailwindcss`: `4.2.4`
- `@tailwindcss/postcss`: `4.2.4`
- `postcss`: `8.5.14`
- `@tanstack/react-query`: `5.100.9`
- `axios`: `1.16.0`
- `zustand`: `5.0.13`
- `react-hook-form`: `7.75.0`
- `zod`: `4.4.3`
- `lightweight-charts`: `5.2.0`
- `lucide-react`: `1.14.0`
- `eslint`: `9.39.4`
- `eslint-config-next`: `16.2.6`
- `@types/node`: `25.6.2`
- `@types/react`: `19.2.14`
- `@types/react-dom`: `19.2.3`

Note: ESLint 10 was available, but the current `eslint-config-next` plugin chain is still compatible with ESLint 9.x. The project uses the newest compatible ESLint 9 release so linting remains reliable.

## Current Progress
- Iteration 1 is complete: foundation, strict TypeScript, Tailwind, typed API client, and React Query provider are in place.
- Iteration 2 is complete: shared UI primitives, dashboard shell, signal queue, signal cards, and Zustand filters are in place.
- Iteration 3 is complete: typed mock candlestick data, chart overlays, pair detail pages, and signal reasoning views are in place.
- Iteration 4 is complete: validated signal filters, richer loading/empty/error states, backend signal/pair integration, responsive cleanup, and build checks are in place.
- Iteration 5 is complete: app-wide navigation shell, real `/dashboard`, `/signals`, and `/analysis` routes, URL-synced filters, route boundaries, breadcrumbs, and active-route highlighting are in place.
- Iteration 6 is complete: server-side signal pagination/filtering (load-more, URL-driven `pair`/`run`), an indicator snapshot panel (RSI/MACD/EMA/BB/ATR), `ai_provider`/`ai_model` + a live `expires_at` freshness badge + entry→SL/TP distance percentages, analysis-runs observability (status filter, pagination, `/analysis/[runId]` detail with signals-per-run), a wired "Trigger analysis run" button, and a new signal-level-map chart driven by signal levels + indicators (the mock-candle dependency was removed).
- Iteration 7 is complete: React Query auto-refresh (`refetchInterval`) with live "updated Xs ago" timestamps, functional notifications (new-signal toast + bell dropdown feed), a Cmd/Ctrl+K command palette with global search across pairs/signals plus quick actions, and persisted UI prefs (density + last route) in `localStorage`.
- The first screen is now a luxury fintech operations dashboard using a black, gold, blue, and red visual system backed by live backend signal endpoints with typed mock fallback for local preview.
- Dynamic routes now exist for `/pairs/[symbol]` and `/signals/[signalId]`.
- Backend health remains wired to `GET /api/v1/health`.
- `any` is not allowed by ESLint (`@typescript-eslint/no-explicit-any: error`).
- `postcss` is overridden to `8.5.14` so `npm audit --audit-level=moderate` reports no vulnerabilities.
- Verified with `npm run check` and local route probes returning `200 OK` for `/`, `/dashboard`, `/signals`, `/analysis`, `/analysis/[runId]`, `/pairs/XAUUSD`, and `/signals/sig-xauusd-1` (and `404` for unknown routes).
- Next up: Iteration 8 (Quality & Production: tests, a11y, SEO, monitoring, perf). See **Planned Work** below.

## Setup Commands
```bash
cd frontend
npm init -y
npm install next@16.2.6 react@19.2.6 react-dom@19.2.6 axios@1.16.0 @tanstack/react-query@5.100.9 zustand@5.0.13 react-hook-form@7.75.0 zod@4.4.3 lightweight-charts@5.2.0 lucide-react@1.14.0 clsx@2.1.1 class-variance-authority@0.7.1 tailwind-merge@3.5.0
npm install -D typescript@6.0.3 @types/node@25.6.2 @types/react@19.2.14 @types/react-dom@19.2.3 tailwindcss@4.2.4 @tailwindcss/postcss@4.2.4 postcss@8.5.14 eslint@9.39.4 eslint-config-next@16.2.6
```

## Iterations and Points

### Iteration 1 - Foundation (13 points)
- [x] (3) Create Next app structure (`src/app`, layouts, route groups)
- [x] (2) Configure TypeScript, ESLint, path aliases
- [x] (3) Configure Tailwind and global styles
- [x] (3) Setup API layer (`axios` client + interceptors)
- [x] (2) Setup React Query provider

### Iteration 2 - Core UI (16 points)
- [x] (3) Build shared UI components (`Button`, `Card`, `Badge`, `LoadingSpinner`)
- [x] (5) Build dashboard page shell
- [x] (5) Build signal list + signal card components
- [x] (3) Add Zustand stores for UI + filters

### Iteration 3 - Trading Views (18 points)
- [x] (8) Implement candlestick chart with `lightweight-charts`
- [x] (4) Implement signal overlays (Entry/SL/TP lines)
- [x] (3) Build pair detail page
- [x] (3) Build signal details page with reasoning panel

### Iteration 4 - Quality + Delivery (13 points)
- [x] (3) Form validation with `react-hook-form` + `zod`
- [x] (4) Loading, empty, error states
- [x] (3) Responsive QA (mobile + desktop)
- [x] (3) Build checks + lint cleanup

Subtotal (Iterations 1-4): 60 points — **complete**

---

## Planned Work (Iterations 5-8)

A senior review on 2026-05-31 surfaced the gaps below. Iterations 5-8 close them.
Auth/accounts (Phase 2) is intentionally **out of scope** for this plan.

### Known gaps the roadmap addresses
- **Dead UI** wired to state but rendering nothing: the nav tabs
  (Overview/Signals/Risk) don't change the view, the command panel toggle renders
  no panel, the notifications bell is decorative, and `useTriggerAnalysisRun`
  exists but no button calls it.
- **Backend data the UI ignores:** `indicators_snapshot` (RSI/MACD/EMA/BB/ATR),
  `ai_provider`/`ai_model`, and `expires_at` are never surfaced; server-side
  pagination/filtering (`page`/`per_page`/`pair`/`run_id`) is unused — the list
  fetches 50 rows and filters client-side; the `analysis/runs` ledger endpoints
  are unused beyond the dashboard's latest-run blurb.
- **Information architecture:** no real routing/navigation between areas, no
  `/signals` or `/analysis` pages, filters aren't reflected in the URL (not
  shareable), and there are no route-level `loading`/`error`/`not-found`
  boundaries.
- **Freshness:** no polling/auto-refresh, no "updated ago", no new-signal toast.
- **Production readiness:** zero frontend tests (backend has 208), SEO only at the
  root layout, no error monitoring/analytics, UI prefs not persisted.

### Captured decisions
- **Charts are driven from signal data + indicators**, not true OHLCV history.
  No candle endpoint is added; the chart renders entry/SL/TP levels and the
  `indicators_snapshot`, so the existing mock-candle dependency is removed.
- **`/` stays the dashboard**; `/dashboard` is added as an alias. No marketing
  landing page in this phase.
- **Auth/accounts are deferred** to Phase 2 and excluded from Iterations 5-8.

### Iteration 5 - Navigation & Information Architecture (16 points)
- [x] (4) App-wide `Navbar`/`Sidebar` with real Next.js routing (replace the
  view-state nav tabs so navigation actually changes the route)
- [x] (4) Dedicated routes: `/dashboard` (alias of `/`), `/signals` (browse all),
  `/analysis` (run ledger); keep `/` as the dashboard
- [x] (3) URL-synced filters (direction/status/pair/sort in the query string —
  shareable and deep-linkable) backed by the existing Zustand store
- [x] (3) Route boundaries: `loading.tsx`, `error.tsx`, and a custom
  `not-found.tsx`
- [x] (2) Breadcrumbs + active-route highlighting

### Iteration 6 - Real Data Depth (20 points)
- [x] (5) Server-side pagination + filtering for signals (drive `page`/`per_page`/
  `pair`/`run_id` from the UI; add pagination / load-more)
- [x] (4) Indicators panel on the signal detail page (RSI/MACD/EMA/BB/ATR from
  `indicators_snapshot`)
- [x] (3) Surface `ai_provider`/`ai_model`, an `expires_at` countdown/staleness
  badge, and entry→SL/TP distance percentages
- [x] (4) Analysis runs observability: list + run detail + signals-per-run, using
  the unused `analysis/runs` endpoints
- [x] (2) Wire a "Trigger analysis run" button to `useTriggerAnalysisRun` with
  poll-for-result feedback
- [x] (2) Re-base the chart on signal levels + indicators and remove the
  mock-candle dependency

### Iteration 7 - Live & Interactive (16 points)
- [x] (4) Auto-refresh via React Query `refetchInterval` + "updated Xs ago"
  relative timestamps
- [x] (4) Functional notifications: toast on new signal + a bell dropdown feed
- [x] (4) Command palette (Cmd+K) for search + quick actions (replace the dead
  command-panel toggle)
- [x] (2) Persist UI prefs (density, last view) to `localStorage`
- [x] (2) Global search across pairs and signals

### Iteration 8 - Quality & Production (18 points)
- [x] (5) Test suite: Vitest + React Testing Library (component/unit) + Playwright
  (key route smoke tests)
- [x] (3) Accessibility pass (focus management, aria, keyboard navigation)
- [x] (4) SEO: per-page metadata, Open Graph tags, `robots.txt`, `sitemap.xml`
- [x] (3) Error boundary + monitoring hook + lightweight analytics
- [x] (3) Performance: chart resize handling, memoization, bundle check

Subtotal (Iterations 5-8): 70 points — **complete**

**Total: 130 points** 🚀

### Iteration 8 notes
- **Tests:** unit/component tests run under Vitest + React Testing Library
  (`npm run test`, 59 tests across pure libs and components). Playwright key-route
  smoke tests live in `e2e/` (`npm run e2e:install` then `npm run e2e`) and boot
  their own production server. `npm run check` now also runs the Vitest suite.
- **Accessibility:** skip-to-content link, `aria-current` on active nav, a focus
  trap + focus restore in the command palette, `aria-expanded`/Escape on the
  notification bell, `aria-pressed` toggles, and an `aria-label`led level-map.
- **SEO:** title template + Open Graph/Twitter + `metadataBase` in the root
  layout, per-route `metadata`/`generateMetadata`, and `app/robots.ts` +
  `app/sitemap.ts`. Canonical origin comes from `NEXT_PUBLIC_SITE_URL`.
- **Resilience:** `app/global-error.tsx` plus a pluggable `lib/monitoring.ts`
  reporter wired into both error boundaries, and a pluggable `lib/analytics.ts`
  sink (pageviews + key events).
- **Performance:** the chart is a pure %-positioned `SignalLevelMap` (no OHLCV
  feed, inherently responsive — the old `ResizeObserver` is gone), `SignalCard`
  is memoised, and list filtering is memoised.

## Run
```bash
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

## Verify
```bash
cd frontend
npm run check          # typecheck + lint + vitest + build
npm run test           # unit/component tests only
npm run e2e:install    # one-time: download the Playwright browser
npm run e2e            # key-route smoke tests (boots its own server)
npm audit --audit-level=moderate
```

## Env
Add the canonical origin used for SEO metadata/robots/sitemap:

```env
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

## Env
Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_NAME=TradeSignal AI
```
