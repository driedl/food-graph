# ADR-0001 — Python-only runner

**Status:** Accepted  
**Date:** 2025-10-02

## Context
Legacy ETL mixed Python (compiler) with a TS runner. We are expanding from 5 to 11+ stages and require deterministic caching and a richer validation layer.

## Decision
Adopt a **Python-only** runner (CLI + direct stage execution). Keep the legacy TS runner intact under `etl/` until parity.

## Consequences
- One language surface for build logic and tests.
- Easier local + CI story.
- We still support the API’s TS/Node world by writing the same SQLite + JSONL artifacts.
