# Scripts

Last reviewed: 2025-10-05

## Purpose

Developer utilities for aggregating code, inspecting API routes, syncing the database, and general maintenance.

## Key Scripts

- `aggregate/aggregate.ts` — Aggregates code/config for LLM context
  - Configs: `aggregate/default.json`, `aggregate/api.json`, `aggregate/etl.json`
  - Usage: `pnpm ag --categories monorepo` (see default config)
- `print-trpc-routes.ts` — Lists API routes
- `run-sql.ts` — Run SQL queries against the SQLite DB
- `sync-db.ts` — Sync database paths and artifacts
- `stop-all.sh` — Kill lingering dev processes (supports flags)

## Outputs

- Aggregates are written under `generated/` (e.g., `generated/code.md`, `generated/code.zip`)

## Related Docs

- `docs/13_MONOREPO_OPTIMIZATION.md`
- `agent/AGENT_GUIDE.md`
