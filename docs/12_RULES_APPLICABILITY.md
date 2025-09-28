# 12 — Applicability Rules & “Dressing” Nodes

_Last updated: 2025-09-28_

This doc standardizes **where metadata lives** (registries), **how applicability is declared** (rules), and **how nodes get “dressed”** at compile time. It also defines minimal DB tables and API affordances to make this usable in the UI.

## Big picture

- **Taxonomy stays biological.** Taxa files contain lineage only.
- **Registries** (global vocab): `attributes.json`, `parts.json`, `transforms.json`, `nutrients.json`.
- **Rules** (scopes/applicability): small JSONL files that attach registries to taxon subtrees and (optionally) parts.
- **Overrides** (rare): per-taxon exceptions inline in taxa items.
- **Overlays** (UX-only): extra labelings/mappings; never identity (e.g., market cut names).

## File layout

```
data/
  ontology/
    taxa/**/*.jsonl                 # biological lineage only
    attributes.json                 # registry
    parts.json                      # registry (IDs, names, optional baseline applies_to)
    transforms.json                 # registry (IDs, params)
    nutrients.json                  # registry
    rules/
      parts_applicability.jsonl     # which parts apply to which taxon subtrees
      transform_applicability.jsonl # (optional v0) allowed transforms by taxon/part
      attribute_scopes.jsonl        # (optional v0) where attributes may attach
      defaults.jsonl                # (optional) param defaults by context
    overlays/
      anatomy_map.jsonl             # (optional) UX mapping of cut vocab (market ↔ canonical parts)
```

> Keep registries centralized. Use `rules/` to _apply_ them to taxa; use overlays to help search/UX.

## IDs & naming (new animal parts)

- Use a hierarchical **part** namespace:
  - Cuts: `part:cut:belly`, `part:cut:loin`, `part:cut:shoulder`, `part:cut:ham`, `part:cut:ribs`, `part:cut:brisket`, `part:cut:round`
  - Organs: `part:organ:liver`, `part:organ:kidney`, `part:organ:heart`
  - Fat: `part:fat:leaf`, `part:fat:subcutaneous`

- Keep `parts.json` entries species-agnostic; scope them via `rules/parts_applicability.jsonl`.
- Continue to use existing plant parts (`part:grain`, etc.).

## Rules (JSONL) — shapes & examples

### 1) `rules/parts_applicability.jsonl` (v0: **required**)

Each line declares that a **part** is valid for a taxon subtree. Expansion uses **prefix matching** on taxon IDs (e.g., `tx:animalia:chordata:mammalia` applies to all descendants).

```json
{"part":"part:muscle","applies_to":["tx:animalia:chordata:mammalia"]}
{"part":"part:cut:belly","applies_to":["tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus"]}
{"part":"part:cut:loin","applies_to":["tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus","tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus"]}
{"part":"part:organ:liver","applies_to":["tx:animalia:chordata:mammalia","tx:animalia:chordata:aves"]}
{"part":"part:milk","applies_to":["tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus"]}
```

Optional fields:

```json
{
  "part": "part:cut:belly",
  "applies_to": ["tx:...:sus:scrofa_domesticus"],
  "exclude": ["tx:...:miniature_breed_x"]
}
```

**Precedence** when compiling:

1. Per-taxon `overrides.disallow_parts` / `overrides.allow_parts`
2. Most-specific rule (longest taxon prefix) wins
3. `parts.json` built-in `applies_to` (fallback)

### 2) `rules/transform_applicability.jsonl` (optional for v0)

Declare which transforms (and param subsets) are allowed, optionally scoped to parts.

```json
{"transform":"tf:cook","applies_to_taxa":["tx:animalia"],"applies_to_parts":["part:muscle","part:cut:*"],"params":{"method":["smoke","roast","boil","fry"]}}
{"transform":"tf:cure","applies_to_taxa":["tx:animalia:...:suidae"],"applies_to_parts":["part:cut:belly","part:cut:loin"]}
```

Wildcards allowed in `applies_to_parts` suffix (`part:cut:*`).

### 3) `rules/attribute_scopes.jsonl` (optional for v0)

Where an attribute may attach (node kind + contextual constraints). Start simple; enforce in UI/API.

```json
{"attr":"attr:lean_pct","attach_to":["FoodState"],"parts":["part:muscle","part:cut:*"],"taxa":["tx:animalia:chordata:mammalia"]}
{"attr":"attr:enrichment","attach_to":["FoodState"],"taxa":["tx:plantae:poaceae"]}
```

### 4) `rules/defaults.jsonl` (optional)

Contextual defaults for transform params.

```json
{
  "context": {
    "taxon_prefix": "tx:plantae:poaceae:avena",
    "part": "part:grain",
    "transform": "tf:mill"
  },
  "defaults": { "refinement": "rolled" }
}
```

## Overrides (rare, inline in taxa)

Add an optional `overrides` object to taxa items when truly exceptional:

```json
{
  "id": "tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus",
  "...": "...",
  "overrides": {
    "disallow_parts": ["part:egg"],
    "allow_parts": ["part:fat:leaf"]
  }
}
```

## Compiler changes (minimal v0)

Extend `etl/py/compile.py`:

1. **Load registries** into new tables (read-only):

   ```sql
   CREATE TABLE IF NOT EXISTS part_def(
     id TEXT PRIMARY KEY,
     name TEXT NOT NULL,
     kind TEXT,
     notes TEXT
   );
   CREATE TABLE IF NOT EXISTS transform_def(
     id TEXT PRIMARY KEY,
     name TEXT NOT NULL,
     identity INTEGER NOT NULL,
     params_json TEXT NOT NULL
   );
   CREATE TABLE IF NOT EXISTS nutrient_def(
     id TEXT PRIMARY KEY,
     name TEXT NOT NULL,
     unit TEXT NOT NULL,
     short_name TEXT
   );
   -- attr_def already exists
   ```

2. **Materialize applicability** (expand prefixes → rows):

   ```sql
   CREATE TABLE IF NOT EXISTS has_part(
     taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
     part_id  TEXT NOT NULL REFERENCES part_def(id) ON DELETE RESTRICT,
     PRIMARY KEY (taxon_id, part_id)
   );
   ```

   - Read `rules/parts_applicability.jsonl`, expand `applies_to` by prefix against existing `nodes.id`, subtract `exclude`, then write `has_part`.
   - Apply per-taxon `overrides` after rule expansion.

3. (Later) **Allowed transforms / attribute scopes**:

   ```sql
   CREATE TABLE IF NOT EXISTS allowed_transform(
     taxon_id TEXT NOT NULL,
     part_id  TEXT,
     transform_id TEXT NOT NULL,
     params_schema_json TEXT,
     PRIMARY KEY(taxon_id, part_id, transform_id)
   );
   CREATE TABLE IF NOT EXISTS attribute_scope(
     attr TEXT NOT NULL,
     attach_to TEXT NOT NULL, -- e.g., 'FoodState'
     taxon_id TEXT,
     part_id TEXT,
     PRIMARY KEY(attr, attach_to, COALESCE(taxon_id,''), COALESCE(part_id,''))
   );
   ```

## API additions (read-only)

- `taxonomy.getPartsForTaxon({ id }) → { part_id, name, kind }[]`
  Backed by `has_part` with a simple `SELECT ... WHERE taxon_id IN (self + ancestors)` for graceful fallback.
- (Later) `taxonomy.getAllowedTransforms({ taxonId, partId? })`
- (Later) `taxonomy.getAttributeScopes({ taxonId, partId? })`

## Validation & QA

- **Schema checks** for rules files (lint in CI).
- **Dangling refs**: every `part_id`, `transform_id`, `attr` must exist in its registry.
- **Coverage report** (optional): count of `has_part` per major clade (quick sanity).
- **Conflict detection**: overlapping rules with contradictory intent → warn; most-specific wins.

## Bacon (worked example shape)

- Identity path uses **part + transforms**, not taxonomy names:

  ```
  fs://animalia/chordata/mammalia/artiodactyla/suidae/sus/scrofa_domesticus
    /part:cut:belly
    /tf:cure{mode=dry,salt_level=regular}
    /tf:cook{method=smoke}
  ```

- `rules/parts_applicability.jsonl` grants `part:cut:belly` to pork.
- (Optional) `overlays/anatomy_map.jsonl` maps “bacon / pancetta / back bacon” to canonical part+process for search only.

## Baby steps (implementation order)

1. Create `data/ontology/rules/parts_applicability.jsonl` with a **minimal seed** (pork belly/loin; beef brisket/round; organs; milk for cow).
2. Extend compiler to load `part_def` and materialize `has_part`.
3. Add `taxonomy.getPartsForTaxon`.
4. Iterate on animal part coverage; then introduce `tf:cure` + `smoke` method in transforms and, if needed, `transform_applicability.jsonl`.

---

**Notes for editors**

- Keep taxa files free of process/market terms.
- Prefer rules/overlays over per-taxon overrides; use overrides sparingly.
- When in doubt, scope via broader prefixes first, then introduce more-specific rules as needed.

---
