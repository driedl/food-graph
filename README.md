# Nutrition Graph Starter

Monorepo starter using **pnpm**, **Vite (React)**, **Fastify**, **tRPC**, **Tailwind**, and **shadcn-style** UI components.
- API: `apps/api` (Fastify + tRPC + SQLite via better-sqlite3)
- Web: `apps/web` (Vite React + tRPC client + React Flow + Tailwind + shadcn-style components)

## Quick start

```bash
pnpm install
pnpm dev
```

- API: http://localhost:3000
- Web: http://localhost:5173

### Notes
- First run will create `apps/api/data/graph.db` and seed a minimal ontology.
- You can regenerate the DB by deleting that file and restarting the API.
