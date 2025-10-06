# ADR-0002 — Package name and paths

**Status:** Accepted  
**Date:** 2025-10-02

## Decision
Name the new ETL package **graph**. Default build root at `etl/build` with the following subdirs:

- `tmp/` intermediates
- `out/` API-ready
- `graph/` edges and substrate lists
- `database/` SQLite
- `report/` lints and stage reports

## Rationale
Short, memorable; “graph en place” captures the philosophy: prep, order, repeatability.
