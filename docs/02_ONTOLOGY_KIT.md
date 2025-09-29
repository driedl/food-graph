# 02 — Ontology Kit (Authoring → Compile)

## Files & Formats

- **Taxa**: NDJSON in `data/ontology/taxa/*.jsonl` — one JSON object per line:
  ```json
  {
    "id": "tx:plantae:rosaceae:malus:domestica",
    "parent": "tx:plantae:rosaceae:malus",
    "rank": "species",
    "display_name": "Apple",
    "latin_name": "Malus domestica",
    "aliases": ["apple"],
    "tags": ["foundation"]
  }
  ```
- **Attributes**: `data/ontology/attributes.json` — registry with roles and kinds.
- **Parts**: `data/ontology/parts.json`
- **Transforms**: `data/ontology/transforms.json`
- **Nutrients**: `data/ontology/nutrients.json`

> Large lists stay in NDJSON for clean diffs and line-by-line validation.

## Compile (v0.1)

The compiler ingests **Taxa + Synonyms + Attribute registry** and writes a SQLite DB:

```bash
pnpm db:build
# -> data/builds/graph.dev.sqlite
```

Current tables:

- `nodes(id, name, slug, rank, parent_id)`
- `synonyms(node_id, synonym)`
- `node_attributes(node_id, attr, val)` — reserved for future authoring
- `attr_def(attr, kind)` — from attributes registry

Future compiles will add:

- `foodstate`, `mixture`, `transform_def`, `evidence`, and materialized rollups.
- Validation report and ID churn report (planned).

## Validation (near-term)

- JSON Schema checks on taxa items (required keys, valid ranks).
- Parent existence and acyclicity checks.
- No process terms in taxonomy names (see Conventions).
