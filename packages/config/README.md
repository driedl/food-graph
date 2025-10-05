# Config (Zod + Paths)

Last reviewed: 2025-10-05

## Purpose

Centralized environment configuration and path utilities for the monorepo.

## Entrypoints & Key Files

- `src/index.ts` — Zod schemas and runtime validation for env vars
- `src/paths.ts` — Repo path helpers

## Common Environment Variables

- `PORT` — API server port (default 3000)
- `DB_PATH` — SQLite database path used by API
- `GRAPH_DB_PATH` — ETL2 database path (preferred for build outputs)
- `GRAPH_BUILD_ROOT` — ETL2 build root (optional)

## Consumers

- `apps/api` (primary)

## Directory Map

```
packages/config/
  src/
    index.ts
    paths.ts
  tsconfig.json
  package.json
```

## Related Docs

- `docs/11_STORAGE_AND_ARTIFACTS.md`
