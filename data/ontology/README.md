# Ontology Authoring

Last reviewed: 2025-10-05

## Purpose

Canonical, Git-first definitions for taxa, parts, transforms, attributes, nutrients, and rules that define the food graph.

## Structure

- `taxa/` — Hierarchy across kingdoms; `.md` docs and `.jsonl` indices
- `attributes.json` — Attribute registry and semantics
- `nutrients.json` — Nutrient catalog
- `parts.json` — Edible/anatomical parts
- `transforms.json` — Processing transform families and parameter schemas
- `categories.json` — Domain categories for UI/ETL convenience
- `rules/` — Domain rules (applicability, expansions, synonyms, param buckets)

## Authoring Conventions

- JSONL newline-delimited records for large lists (`*.jsonl`)
- Deterministic IDs and stable prefixes (`tx:`, `attr:`)
- Prefer additive changes; avoid rewrites that break IDs
- See schemas in `data/sql/schema/` for DB shapes and validation intentions

## How this feeds ETL

- ETL reads from `data/ontology/**` and produces:
  - Normalized artifacts under `etl/build/compiled/`
  - A SQLite DB at `etl/build/database/graph.dev.sqlite`
  - Validation reports under `etl/build/report/`

## File Type Notes

- `.tx.md` documentation files may include YAML frontmatter to annotate taxa
- `.jsonl` indexes allow streaming validation and partial rebuilds

## Quick QA checklist (NDJSON hygiene)

**IDs & prefixes**

- Use stable prefixes: `tx:` for taxa, `attr:` for attributes.
- IDs are lowercase, snake/kebab acceptable; never embed spaces.
- Children must have valid existing `parent` IDs (no dangling references).

**Ranks & kinds**

- Taxa must have a valid `rank` from {kingdom, family, genus, species, variety, cultivar, form}.
- Attributes must set `"kind":"attribute"` (no `rank` field).

**Names**

- `display_name`: human-readable, title-case where natural (“Potato (Yukon Gold)”).
- `latin_name`: scientific binomial when applicable; empty string `""` only for purely synthetic nodes.
- Avoid marketing adjectives in `display_name` (e.g., “premium”, “fresh”).

**Aliases**

- Include common spellings and plurals (e.g., “pistachio”, “pistachios”).
- No duplicates; no capitalization variants unless meaning changes.

**Attributes**

- Every attribute defines: `datatype`, `cardinality`, `default`, and either `enum` or `unit`.
- `normalize_terms` only maps real-world labels → canonical values; do not include regex in NDJSON.
- `applies_to` should be broad (e.g., a kingdom/family) unless truly specific.

**Dupes & conflicts**

- Before adding, run a de-dupe pass by `display_name` (case-insensitive) and by `latin_name`.
- If two nodes represent the same thing at different ranks, prefer the **lower** valid rank (e.g., species over genus).

**Tags**

- Keep tags compact and functional (e.g., `["foundation"]` for core staples, `["facet"]` for UI filters).

**Consistency spot-checks (per PR)**

- Pick 5 random lines: confirm JSON validity, required keys present, and parent chain resolves to a kingdom.
- Confirm new `attr:` IDs show in UI facet registry (once we wire it).
