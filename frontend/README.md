# 🎨 Frontend Setup - TradeSignal AI

## ✅ Goal
Create a modern **Next.js + React + TypeScript** frontend with all required packages for dashboards, charts, forms, state, and API integrations.

## 📌 Latest Versions (verified on 2026-04-22)
- `next`: `16.2.4`
- `react`: `19.2.5`
- `react-dom`: `19.2.5`
- `typescript`: `6.0.3`
- `tailwindcss`: `4.2.4`
- `@tailwindcss/postcss`: `4.2.4`
- `postcss`: `8.5.10`
- `@tanstack/react-query`: `5.99.2`
- `axios`: `1.15.2`
- `zustand`: `5.0.12`
- `react-hook-form`: `7.73.1`
- `zod`: `4.3.6`
- `lightweight-charts`: `5.1.0`
- `eslint`: `10.2.1`
- `eslint-config-next`: `16.2.4`
- `@types/node`: `25.6.0`
- `@types/react`: `19.2.14`
- `@types/react-dom`: `19.2.3`

## ⚡ Setup Commands
```bash
cd frontend
npm init -y
npm install next@16.2.4 react@19.2.5 react-dom@19.2.5 axios@1.15.2 @tanstack/react-query@5.99.2 zustand@5.0.12 react-hook-form@7.73.1 zod@4.3.6 lightweight-charts@5.1.0 clsx@2.1.1 class-variance-authority@0.7.1 tailwind-merge@3.5.0
npm install -D typescript@6.0.3 @types/node@25.6.0 @types/react@19.2.14 @types/react-dom@19.2.3 tailwindcss@4.2.4 @tailwindcss/postcss@4.2.4 postcss@8.5.10 eslint@10.2.1 eslint-config-next@16.2.4
```

## 🧩 Iterations and Points

### Iteration 1 - Foundation (13 points)
- [ ] (3) Create Next app structure (`src/app`, layouts, route groups)
- [ ] (2) Configure TypeScript, ESLint, path aliases
- [ ] (3) Configure Tailwind and global styles
- [ ] (3) Setup API layer (`axios` client + interceptors)
- [ ] (2) Setup React Query provider

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
npm run dev
```

## 🔐 Env
Create `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_NAME=TradeSignal AI
```
