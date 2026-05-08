# 🎨 Frontend Setup - TradeSignal AI

## ✅ Goal
Create a modern **Next.js + React + TypeScript** frontend with all required packages for dashboards, charts, forms, state, and API integrations.

## 📌 Installed Versions (verified on 2026-05-08)
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
- `eslint`: `9.39.4`
- `eslint-config-next`: `16.2.6`
- `@types/node`: `25.6.2`
- `@types/react`: `19.2.14`
- `@types/react-dom`: `19.2.3`

> Note: ESLint 10 was available, but the current `eslint-config-next` plugin chain is still compatible with ESLint 9.x. The project uses the newest compatible ESLint 9 release so linting remains reliable.

## 📍 Current Progress
- Iteration 1 is complete: foundation, strict TypeScript, Tailwind, typed API client, and React Query provider are in place.
- The first screen is a health-backed dashboard shell wired to `GET /api/v1/health`.
- `any` is not allowed by ESLint (`@typescript-eslint/no-explicit-any: error`).
- `postcss` is overridden to `8.5.14` so `npm audit --audit-level=moderate` reports no vulnerabilities.
- Verified with `npm run check` and a local smoke test returning `HTTP/1.1 200 OK`.

## ⚡ Setup Commands
```bash
cd frontend
npm init -y
npm install next@16.2.6 react@19.2.6 react-dom@19.2.6 axios@1.16.0 @tanstack/react-query@5.100.9 zustand@5.0.13 react-hook-form@7.75.0 zod@4.4.3 lightweight-charts@5.2.0 clsx@2.1.1 class-variance-authority@0.7.1 tailwind-merge@3.5.0
npm install -D typescript@6.0.3 @types/node@25.6.2 @types/react@19.2.14 @types/react-dom@19.2.3 tailwindcss@4.2.4 @tailwindcss/postcss@4.2.4 postcss@8.5.14 eslint@9.39.4 eslint-config-next@16.2.6
```

## 🧩 Iterations and Points

### Iteration 1 - Foundation (13 points)
- [x] (3) Create Next app structure (`src/app`, layouts, route groups)
- [x] (2) Configure TypeScript, ESLint, path aliases
- [x] (3) Configure Tailwind and global styles
- [x] (3) Setup API layer (`axios` client + interceptors)
- [x] (2) Setup React Query provider

### Iteration 2 - Core UI (16 points)
- [ ] (3) Build shared UI components (`Button`, `Card`, `Badge`, `LoadingSpinner`)
- [ ] (5) Build dashboard page shell
- [ ] (5) Build signal list + signal card components
- [ ] (3) Add Zustand stores for UI + filters

### Iteration 3 - Trading Views (18 points)
- [ ] (8) Implement candlestick chart with `lightweight-charts`
- [ ] (4) Implement signal overlays (Entry/SL/TP lines)
- [ ] (3) Build pair detail page
- [ ] (3) Build signal details page with reasoning panel

### Iteration 4 - Quality + Delivery (13 points)
- [ ] (3) Form validation with `react-hook-form` + `zod`
- [ ] (4) Loading, empty, error states
- [ ] (3) Responsive QA (mobile + desktop)
- [ ] (3) Build checks + lint cleanup

**Total: 60 points** 🚀

## 🧪 Run
```bash
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

## ✅ Verify
```bash
cd frontend
npm run check
npm audit --audit-level=moderate
```

## 🔐 Env
Create `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_NAME=TradeSignal AI
```
