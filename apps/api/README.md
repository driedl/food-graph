# API Server (Fastify + tRPC)

Last reviewed: 2025-10-05

## Purpose

TypeScript backend that serves the food graph via a Fastify server and tRPC routers. Reads a compiled SQLite database and exposes taxonomy, search, FoodState, and TPT-related endpoints.

## Responsibilities & Boundaries

- Implements HTTP server, routing, validation, and serialization
- Performs read/compute over a SQLite database (no long-running jobs)
- Publishes strongly-typed contracts consumed by the web app via `@nutrition/api-contract`
- Does not compile ontology or build the database (handled by `etl`)

## Entrypoints & Key Files

- `src/index.ts` — Fastify bootstrap and tRPC wiring
- `src/db.ts` — SQLite connection and helpers
- `src/router/` — tRPC routers: `browse.ts`, `search.ts`, `taxa.ts`, `evidence.ts`, `tpt*.ts`, etc.
- `src/lib/` — server-side helpers and domain utilities

## Configuration

- `PORT` — Fastify port (default 3000)
- `DB_PATH` — SQLite file path. Recommended to point at the ETL output
  - Example: `DB_PATH=etl/build/database/graph.dev.sqlite`
- Optional: `GRAPH_DB_PATH` used by scripts; prefer `DB_PATH` for the API

Environment files: create `apps/api/.env` and set `PORT`, `DB_PATH`.

## Run & Build

From repo root:

```bash
pnpm dev:api          # Dev mode (via Turbo)
pnpm -C apps/api dev  # Direct dev
pnpm -C apps/api build
pnpm -C apps/api typecheck
```

If the database is missing, generate it first (see ETL2 below).

## Database

The API uses a SQLite database that is compiled from the Git-authored ontology.

- Recommended: build with ETL and point `DB_PATH` to `etl/build/database/graph.dev.sqlite`
- For quick inspection: `pnpm db:open` (opens ETL DB if present)

## Interactions

- Consumes: SQLite DB from `etl`
- Shares types: `@nutrition/shared`
- Exposes types: `@nutrition/api-contract` for the web client

## Development Utilities

- `scripts/print-trpc-routes.ts` — inspect published routes
- `scripts/run-sql.ts` — ad-hoc SQL queries against the DB

## Directory Map

```
apps/api/
  src/
    db.ts
    index.ts
    lib/
    router/
  scripts/
  tsconfig.json
  package.json
```

## Related Docs

- `docs/01_ARCHITECTURE.md`
- `docs/11_STORAGE_AND_ARTIFACTS.md`
- `etl/README.md`


