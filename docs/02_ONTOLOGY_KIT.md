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

The compiler is a multi-step Python pipeline that ingests ontology data and writes a SQLite DB:

```bash
pnpm etl:build
# -> etl/dist/database/graph.dev.sqlite
```

**Pipeline steps:**

1. Validate ontology data (schema checks, parent existence)
2. Compile taxa from `.tx.md` frontmatter → `taxa.jsonl`
3. Compile documentation from `.tx.md` content → `docs.jsonl`
4. Build SQLite database with all ontology data
5. Verify database integrity and FTS functionality
6. Generate documentation coverage report

**Current tables:**

- **Taxonomy**: `nodes`, `synonyms`, `node_attributes`, `attr_def`, `attr_enum`
- **Documentation**: `taxon_doc` (markdown docs per taxon)
- **Parts**: `part_def`, `part_synonym`, `has_part`
- **Transforms**: `transform_def`, `transform_applicability`
- **Search**: `taxa_fts` (FTS5 index for taxa), `tp_fts` (FTS5 index for taxon+part)

**Future compiles will add:**

- `foodstate`, `mixture`, `evidence`, `classifications`, `functional_class`, `labelings`, and materialized rollups.
- ID churn detection and reporting.

## Validation (near-term)

- JSON Schema checks on taxa items (required keys, valid ranks).
- Parent existence and acyclicity checks.
- No process terms in taxonomy names (see Conventions).
