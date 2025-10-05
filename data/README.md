# Data Directory

Last reviewed: 2025-10-05

## Purpose

Authoritative sources (ontology), external inputs, schemas, and tests used to build the graph database via ETL2.

## Structure

- `ontology/` — Git-first canonical ontology (JSON/JSONL/MD)
- `sources/` — External raw data (e.g., USDA FDC)
- `sql/schema/` — JSON schema definitions for the SQLite database
- `tests/` — Smoke and validation fixtures for data-level QA

## Interactions

- Inputs to ETL (see `etl/README.md`)
- Output artifacts (compiled/canon forms) are written under `etl/build` by the pipeline

## Authoring Quicklinks

- `ontology/README.md` — Authoring rules, structure, and QA checklist
- Schemas under `sql/schema/` — shapes used for DB tables and validations

## Directory Map

```
data/
  ontology/
  sources/
  sql/
    schema/
  tests/
```

## Related Docs

- `docs/02_ONTOLOGY_BIBLE.md`
- `docs/11_STORAGE_AND_ARTIFACTS.md`
