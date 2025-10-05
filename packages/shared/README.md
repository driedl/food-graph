# Shared Types (TypeScript)

Last reviewed: 2025-10-05

## Purpose

Centralized TypeScript types and helpers shared across API and Web. Encapsulates domain types for taxonomy, FoodState, and related utilities.

## Entrypoints & Key Files

- `src/index.ts` — Main export surface
- `src/foodstate.ts` — FoodState-related types and helpers

## Consumers

- `apps/api` — runtime and router types
- `apps/web` — UI models and API client types
- `packages/api-contract` — composes AppRouter types

## Guidelines

- Keep the surface stable and additive; prefer new fields over breaking renames
- Avoid runtime dependencies beyond lightweight utilities

## Directory Map

```
packages/shared/
  src/
    foodstate.ts
    index.ts
  tsconfig.json
  package.json
```

## Related Docs

- `docs/01_ARCHITECTURE.md`


