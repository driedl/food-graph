# Web App (Vite + React + TanStack Router)

Last reviewed: 2025-10-05

## Purpose

Interactive explorer UI for the food graph. Renders taxonomy, FoodStates, and TPT insights while consuming the API via tRPC with end-to-end type safety.

## Responsibilities & Boundaries

- Client-side navigation and data fetching via TanStack Router + React Query
- Visualization and inspector components (graph, panels, overlays)
- No server-side rendering; relies on API for data and computation

## Entrypoints & Key Files

- `src/main.tsx` — App bootstrap
- `src/routes/` — Pages and workbench routes (e.g., `workbench.*.tsx`)
- `src/lib/trpc.ts` — tRPC client setup (AppRouter types from `@nutrition/api-contract`)
- `src/components/` — Graph and inspector components

## Configuration

- Vite dev server: `vite.config.ts`
- Tailwind and PostCSS: `tailwind.config.ts`, `postcss.config.js`
- API proxy: configure in Vite if API origin differs

## Run & Build

From repo root:

```bash
pnpm dev:web          # Dev mode (via Turbo)
pnpm -C apps/web dev  # Direct dev
pnpm -C apps/web build
pnpm -C apps/web typecheck
```

## Interactions

- Consumes: `@nutrition/api-contract` types; tRPC server in `apps/api`
- Shared types: `@nutrition/shared`

## Directory Map

```
apps/web/
  src/
    components/
    hooks/
    lib/
    routes/
    main.tsx
  tailwind.config.ts
  vite.config.ts
  package.json
```

## Related Docs

- `docs/18_UI-vision-plan.md`
- `docs/01_ARCHITECTURE.md`


