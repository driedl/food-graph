# Ontology Seeding Plan (Foundation 411 + Pantry 100)

This package fixes the NDJSON newline issue (real LF line endings) and sets up a safe path to ingest the **USDA FDC Foundation Foods (≈411)** alongside a curated **Pantry 100** list.

## Why NDJSON here?
- One object per line → clean Git diffs, easier merges
- Streams into SQLite/DuckDB without loading whole files
- Validates line-by-line against JSON Schema before cross-reference checks

## Files
- `data/ontology/taxa/pantry-100.jsonl` — 100 common pantry items as nodes anchored to kingdoms (plants, animals, fungi, minerals).
- `scripts/generate_foundation_taxa.ts` — CLI that reads an official FDC "Foundation Foods" CSV/JSON and emits `foundation-411.jsonl` with **proper LF newlines**.
- `scripts/validate_ndjson.ts` — sanity checker for newline integrity and required keys.
- `.editorconfig` — enforces LF line endings and trailing newline to avoid `\n`/`/n` mishaps.

## Running
```bash
# 1) Generate Foundation 411 NDJSON from an official FDC export
pnpm tsx scripts/generate_foundation_taxa.ts --fdc ./path/to/foundation.csv --out data/ontology/taxa/foundation-411.jsonl

# 2) (Optional) Quick validation
pnpm tsx scripts/validate_ndjson.ts data/ontology/taxa/*.jsonl

# 3) Compile into SQLite for the API
pnpm db:build
```

## About taxonomy precision
- **Pantry 100** is anchored to the correct kingdom and includes species/genus when unambiguous; we keep ranks pragmatic and will refine internal hierarchy (family→genus→species) iteratively.
- **Foundation 411** will be generated from the source export. The generator uses curated heuristics and a growing mapping dictionary to assign a taxon path; items without a confident match are marked with `tags: ["needs_taxonomy"]` for review.

## ID format
- Human-readable, stable IDs: `tx:<scope>:<slug>`, e.g., `tx:plantae:olea-europaea` for olive.
- If the generator can't determine genus/species, it uses a stable fallback under the appropriate kingdom: `tx:plantae:unclassified:<fdc_slug>` and tags it for cleanup.

