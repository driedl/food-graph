# API Contract (tRPC Types)

Last reviewed: 2025-10-05

## Purpose

Exports the tRPC `AppRouter` types from the API so the Web app gets end-to-end type safety for requests and responses.

## Entrypoint

- `src/index.ts` — re-exports `AppRouter` type

## Flow

- Source of truth: API router definitions in `apps/api/src/router/*`
- This package should contain types only (no runtime code)
- The Web app imports these types to bind the tRPC client

## Directory Map

```
packages/api-contract/
  src/
    index.ts
  tsconfig.json
  package.json
```

## Related Docs

- `docs/01_ARCHITECTURE.md`
