# graph — the new ETL for the Food Graph

Last reviewed: 2025-10-05

**graph** (as in *graph en place*) is a Python-first, deterministic build system for the Food Graph.
It replaces ad‑hoc, monolithic scripts with **small, testable stages** and **clear artifacts**.
This is the primary ETL pipeline for the food graph.

- Runner: Python 3.11+ (CLI)
- Artifacts: `etl/build/{tmp,out,graph,database,report}`

## Quickstart

```bash
# install (editable)
python -m pip install -e ./etl

# run the pipeline with tests
python -m graph run build --with-tests

# run the pipeline
python -m graph run build
```

## Inputs & Outputs

- Inputs: `data/ontology/**` (NDJSON/JSON/MD rules, taxa, attributes, nutrients, parts, transforms)
- Outputs: `etl/build/` directories
  - `database/graph.dev.sqlite` — main DB consumed by the API
  - `compiled/` — normalized/compiled JSON artifacts
  - `graph/` — derived graph overlays (e.g., substrates)
  - `report/` — validation and verification reports
  - `tmp/`, `out/` — intermediate stage artifacts

## Stages (overview)

- `stage_0` — Load + compile docs + validate taxa
- `stage_a` — Normalize rules, validate flags, load schemas
- `stage_b` — Build substrates
- `stage_c` — Curated seed building
- `stage_d` — Family expansion
- `stage_e` — Canonical IDs
- `stage_f` — Pack SQLite (`sqlite_pack.py`)

Contracts per stage live in `graph/stages/*/contract.yml` and are validated during runs.

## API Integration

Point the API to the ETL database:

```env
DB_PATH=etl/build/database/graph.dev.sqlite
```

You can also set:

```env
GRAPH_DB_PATH=etl/build/database/graph.dev.sqlite
GRAPH_BUILD_ROOT=etl/build
```

## Testing & CI

- Run tests: `pytest` (or `python -m pytest`)
- Minimal test suite resides under `etl/tests/`
- Determinism checks ensure stable outputs across runs

## Docs & Decision Log

- Overview: `etl/docs/00-overview.md`
- Architecture: `etl/docs/01-architecture.md`
- Stages: `etl/docs/02-stages.md`
- Configuration: `etl/docs/03-configuration.md`
- Schemas: `etl/docs/04-schemas.md`
- Decision log: `etl/docs/09-decision-log/`

### Switch API to use graph outputs

Expose the DB (or other artifacts) to the API via envs:

```
GRAPH_DB_PATH=etl/build/database/graph.dev.sqlite
GRAPH_BUILD_ROOT=etl/build
```
