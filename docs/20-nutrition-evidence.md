# Plan: Add a Nutrition “Evidence Layer” to the Existing Food Ontology — **with concrete evidence-build mechanics**

> This is the complete plan that keeps your ontology fast, clean, and Git-friendly while adding a simple, POC-grade evidence pipeline. I’ve preserved everything valuable from the earlier spec and folded in the specifics for **file-based evidence builds**, **LLM-assisted mapping**, and **how profiles get materialized** without slowing your ontology pack step.

---

## Executive Summary

Public nutrition data arrives as **per-food × per-nutrient** rows, typically **per 100 g EP**, with units, derivations, and preparation states. We’ll keep the ontology (T, TP, TPT) **unchanged**, ingest heterogeneous sources **verbatim** into a **Git-tracked, JSONL evidence layer**, normalize nutrients to **INFOODS tagnames (+ UCUM units)**, and compute **stable per-node profiles** (per 100 g EP) via transparent rollups that preserve provenance.

**POC emphasis**

* No extra DB at ingest time: evidence lives as **JSONL files** in the repo (easy to diff/review).
* Mapping is **LLM-assisted** to propose `(taxon, part, transforms)`; a **human approves** new nodes.
* A separate **profiles build** attaches `graph.db` and turns evidence JSONL into `nutrition_profile_*` tables (in `app.db` or appended to `graph.db` if you prefer), fast and deterministic.
* **Use your existing node IDs** (`taxon_part_nodes.id` and `tpt_nodes.id`) as foreign keys. No new ID scheme.

---

## Goals & Principles (unchanged, tightened)

**Goals**

* Keep T/TP/TPT the **source of truth** for food identity.
* Ingest any dataset (FDC/CIQUAL/CoFID/GDSN/brands) **unchanged** as evidence.
* Normalize nutrients once via **INFOODS** + **UCUM**.
* Attach **provenance to evidence**, not to graph nodes.
* **Roll up** evidence into **per-node profiles** (per 100 g EP) with transparent conflict resolution + versioned policy.
* Be **transform-aware**: TPT identity encodes “as prepared/as eaten”.

**Principles**

* **Evidence lives off-graph**; nodes stay ontology-clean.
* **Canonical basis** = **per 100 g EP** (retain native bases in evidence for provenance).
* **INFOODS tagnames** are canonical nutrient IDs.
* **Reproducible**: same evidence + same config ⇒ same profiles.
* **Imputation** only when necessary; clearly flagged and down-weighted.

---

## Architecture (POC)

* **graph.db** — built by your existing **Stage F** pack (`sqlite_pack.py`). Contains `nodes`, `part_def`, TP/TPT tables, closures, FTS, flags, cuisines, etc. (Fast to rebuild.)
* **evidence/** (Git-tracked) — **JSONL + JSON** files:

  * `<source_id>/foods.jsonl`, `nutrients.jsonl`, `mapping.jsonl`, plus `source.json` (metadata).
  * Global `nutrient_def.json`, `nutrient_alias_map.json`, `rollup_config.json`.
* **app.db** (or `build.db`) — read-optimized artifact with `nutrition_profile_*` (+ optional %DV). Built by **profiles step** that **attaches** `graph.db` and **reads** `evidence/**/*.jsonl`.

> You can also write profiles back into `graph.db` if you want a single DB for the app. For POC, I recommend **separate** `app.db` so your ontology regen remains blazing fast.

---

## Evidence Repository Layout (Git)

```
evidence/
  nutrient_def.json                 # INFOODS-first registry
  nutrient_alias_map.json           # map FDC/CIQUAL/etc. → INFOODS
  rollup_config.json                # versioned knobs (weights/outliers/etc.)

  fdc-2024-09/                      # one folder per source release
    source.json                     # name, version, license, kind, ingest_date
    foods.jsonl                     # external foods (one per line)
    nutrients.jsonl                 # external food × nutrient rows
    mapping.jsonl                   # mapping to TP/TPT node_id (nullable)
    logs/                           # optional ingest reports

  ciqual-2020/
    source.json
    foods.jsonl
    nutrients.jsonl
    mapping.jsonl

  ...more sources...
```

---

## Evidence File Contracts (POC JSONL/JSON)

### `nutrient_def.json` (global)

INFOODS-first registry.

```json
[
  {
    "nutrient_id": "PROCNT",
    "name": "Protein",
    "category": "macro",
    "canonical_unit": "g",
    "precision": 1,
    "is_energy": false,
    "notes": "Total protein"
  },
  {
    "nutrient_id": "ENERC_KCAL",
    "name": "Energy",
    "category": "macro",
    "canonical_unit": "kcal",
    "precision": 0,
    "is_energy": true
  }
]
```

### `nutrient_alias_map.json` (global)

Maps source codes → INFOODS.

```json
{
  "fdc": {
    "1003": "PROCNT",
    "1004": "FAT",
    "1005": "CHOCDF",
    "1008": "ENERC_KCAL"
  },
  "ciqual": { "PROCNT": "PROCNT", "...": "..." }
}
```

### `<source_id>/source.json`

```json
{
  "source_id": "fdc-2024-09",
  "name": "USDA FoodData Central",
  "version": "2024.09",
  "license": "https://...",
  "citation": "...",
  "kind": "foundation",
  "ingest_date": "2025-10-05",
  "default_quality_tier": 1
}
```

### `<source_id>/foods.jsonl`

One line per external food (immutable evidence row).

```json
{"source_id":"fdc-2024-09","external_food_id":"123456","label":"Yogurt, Greek, plain, whole milk","brand":null,"data_type":"Foundation","state":"fermented","prep_method":"strained","edible_portion_flag":true,"serving_size_amount":null,"serving_size_unit":null,"household_measure":null,"density_g_per_ml":null,"country":"US","lang":"en"}
{"source_id":"fdc-2024-09","external_food_id":"789012","label":"Bacon, cooked, pan-fried","data_type":"SR_Legacy","state":"cooked","prep_method":"fried","edible_portion_flag":true}
```

### `<source_id>/nutrients.jsonl`

One line per (food × nutrient). Units/basis **as provided**.

```json
{"source_id":"fdc-2024-09","external_food_id":"123456","nutrient":"PROCNT","amount":10.2,"unit":"g","basis":"per_100g","derivation":"analytical","sample_n":8}
{"source_id":"fdc-2024-09","external_food_id":"123456","nutrient":"ENERC_KCAL","amount":120,"unit":"kcal","basis":"per_100g","derivation":"analytical"}
{"source_id":"fdc-2024-09","external_food_id":"789012","nutrient":"FAT","amount":42,"unit":"g","basis":"per_100g","derivation":"analytical"}
```

> `nutrient` must resolve via `nutrient_alias_map` to an INFOODS tag (reject if unmappable).

### `<source_id>/mapping.jsonl`

**One row per food in `foods.jsonl`.** `node_id` is either the resolved TP/TPT id in `graph.db`, or null (new candidate). Includes LLM suggestion payload for audit.

```json
{
  "source_id":"fdc-2024-09",
  "external_food_id":"123456",
  "node_id":"tpt:bos_taurus:milk:greek_yogurt",        // existing TPT → good
  "node_type":"TPT",
  "confidence":0.93,
  "method":"llm+fts",
  "llm_suggestion":{
    "taxon_hints":["bos taurus","cow"],
    "part_id":"part:milk",
    "transforms":[{"id":"tf:ferment","params":{"starter":"lactobacillus"}},{"id":"tf:strain","params":{"strain_level":10}}],
    "notes":"explicit 'Greek' implies strained yogurt",
    "novelty":{"new_part":null,"new_transform":null}
  }
}
```

If the LLM/curator believes it’s a **new node** (TP or TPT doesn’t exist), leave `node_id:null` and propose identity:

```json
{
  "source_id":"fdc-2024-09",
  "external_food_id":"999999",
  "node_id": null,                                  // candidate
  "node_type":"TPT",
  "confidence":0.78,
  "method":"llm+human",
  "proposed_identity":{
    "taxon_id":"tx:plantae:poaceae:oryza:sativa",
    "part_id":"part:grain",
    "identity_steps":[{"id":"tf:parboil"}],
    "display_name":"Parboiled Rice"
  },
  "llm_suggestion":{ "...": "..." }
}
```

> This is the **single “delta”** you asked about: `node_id` present → use it; `node_id:null` → **candidate** for ontology enrichment (human review).

### `rollup_config.json` (global)

Versioned knobs used by the profiles build (same as before):

```json
{
  "tier_weights":{"1":1.0,"2":0.7,"3":0.5,"4":0.3},
  "outlier_rule":{"method":"mad","k":3},
  "aggregator":{"method":"weighted_median"},
  "confidence_threshold_for_mapping":0.7,
  "energy_reconciliation":{"enabled":true,"tolerance_pct":8},
  "recency_decay":{"apply_to":["branded"],"lambda_per_year":0.05},
  "min_rows_per_profile":2,
  "imputation":{"enabled":true,"max_share_pct":0.2}
}
```

---

## LLM-Assisted Mapping (POC)

**Model**: Use a capable, instruction-following model (e.g., **GPT-5 Thinking** in non-tool, non-chain mode) to produce a **single JSON object** per food.
**Inputs**:

* Food `label`, `brand`, `data_type`, `state`, `prep_method`.
* Top-K candidates from `graph.db.search_fts` (by querying with the label and any detected keywords).
* **Transforms registry** (`transform_def`), **parts list** (`part_def`), **taxon synonyms** (optional hints).

**Output JSON (inline into `mapping.jsonl.llm_suggestion`)**:

```json
{
  "taxon_hints": ["bos taurus"],
  "part_id": "part:milk",
  "transforms": [{"id":"tf:ferment"},{"id":"tf:strain","params":{"strain_level":10}}],
  "attributes": {"attr:fat_pct": 4},
  "notes": "…",
  "novelty": { "new_part": null, "new_transform": null }
}
```

**Post-processing**:

* Resolve **node_id**:

  * If a TPT in `graph.db` matches `(taxon_id, part_id, identity_hash)` (or the canonical signature) → set `node_id`.
  * Else set `node_id:null`, fill `proposed_identity` for human review.
* Add `confidence` (from LLM score × string-match features).

> Keep it **simple**: a single pass per food that writes one line to `mapping.jsonl`. You can re-run just this step for a source without touching other sources.

---

## What changes (lightly) in **graph.db**

You asked to use the existing ID scheme — we will. Two small, optional hardening tweaks help the mapping step:

1. **Uniqueness by identity** (avoid duplicate states)

```sql
-- enforce uniqueness of identity within a TP
CREATE UNIQUE INDEX IF NOT EXISTS uq_tpt_identity
ON tpt_nodes(taxon_id, part_id, identity_hash);
```

2. **(Optional) string signature** for matching (debuggable)

* Add a `signature` TEXT column to `tpt_nodes` (computed in Stage E before pack) as:
  `taxon_id | part_id | normalized(identity-steps)`; optionally `UNIQUE(signature)`.
* Keep `path_json` as the canonical identity path.

Everything else in Stage F remains as-is.

---

## Profiles Build (from evidence → app.db)

A single script/step (call it `profiles:compute`) creates/refreshes nutrition tables by **attaching** your packed ontology.

**Inputs**:

* `graph.db` (from Stage F pack).
* `evidence/**/source.json`, `foods.jsonl`, `nutrients.jsonl`, `mapping.jsonl`.
* `nutrient_def.json`, `nutrient_alias_map.json`, `rollup_config.json`.

**Outputs** (in `app.db` by default):

* `nutrition_profile_current`
* `nutrition_profile_provenance`
* optional `nutrition_profile_history`
* optional `%DV` tables (`daily_value_table`) and `portion_definition`

**Algorithm** (unchanged, now grounded in files):

1. **Load registry**
   Read `nutrient_def.json` and `nutrient_alias_map.json` (reject unmapped nutrients).

2. **Stream evidence**
   Iterate `foods.jsonl` and `nutrients.jsonl`.
   Normalize units to canonical (UCUM) and filter rows convertible to **per 100 g** (via serving+density if needed, else mark excluded).

3. **Join mapping**
   For each external food, read `mapping.jsonl`:

   * If `node_id` present and `confidence ≥ threshold`: route nutrient rows to that node.
   * If `node_id:null`: skip from rollups (but persist as “**candidate**; unmapped” in diagnostics).

4. **QC**

   * Reject negatives unless below-LOD sentinel → coerce to 0, flag.
   * **Energy reconciliation** (if `ENERC_KCAL` and macros present): ±8% tolerance; otherwise flag.

5. **Weighting & Outliers**

   * Weights = `tier_weights[source.kind]` × `log(1+sample_n)` × optional recency decay.
   * Remove outliers (MAD k=3 or P5–P95 trims).

6. **Aggregate**

   * Default aggregator: **weighted median** per `(node_id, nutrient_id)`.
   * Persist into `nutrition_profile_current` + **detailed** `nutrition_profile_provenance` (with `used`, `reason_excluded`).

7. **Summaries & Flags**

   * `provenance_summary` (“FDC Foundation×3; CIQUAL×1; Branded×2”).
   * Flags: `high_variance`, `basis_mixed_filtered`, `%imputed`, etc.

**Tables (same as original spec; POC DDL recap)**

```sql
CREATE TABLE IF NOT EXISTS nutrition_profile_current (
  node_id TEXT NOT NULL,            -- FK to graph.taxon_part_nodes.id or tpt_nodes.id
  nutrient_id TEXT NOT NULL,        -- INFOODS tag
  amount_per_100g REAL NOT NULL,
  basis TEXT NOT NULL DEFAULT 'per_100g',
  method TEXT NOT NULL,             -- weighted_median|... (from config)
  n_sources INTEGER NOT NULL,
  n_rows INTEGER NOT NULL,
  last_recomputed TEXT NOT NULL,
  provenance_summary TEXT,
  flags TEXT,                       -- JSON
  PRIMARY KEY (node_id, nutrient_id)
);

CREATE TABLE IF NOT EXISTS nutrition_profile_provenance (
  node_id TEXT NOT NULL,
  nutrient_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  external_food_id TEXT NOT NULL,
  weight REAL NOT NULL,
  used INTEGER NOT NULL,            -- 1 used; 0 excluded
  reason_excluded TEXT,             -- outlier_high|basis_unconvertible|...
  amount_norm REAL,                 -- normalized to canonical + per_100g
  unit TEXT NOT NULL DEFAULT '',    -- canonical UCUM
  basis TEXT NOT NULL DEFAULT 'per_100g',
  derivation TEXT,                  -- analytical|label|...
  sample_n INTEGER,
  PRIMARY KEY (node_id, nutrient_id, source_id, external_food_id)
);
```

> You can **keep these tables in `app.db`** or attach/appended into `graph.db`. POC default: separate file to keep ontology rebuilds fast.

---

## Ingestion & Normalization Rules (unchanged, now tied to files)

1. **Units & basis**

   * Canonicalize to INFOODS + UCUM; retain original fields in provenance.
   * Prefer **per 100 g EP**; convert from per serving/100 ml when possible, else exclude from rollups (but keep for diagnostics).
   * Energy: support `ENERC_KCAL` and `ENERC_KJ` conversions.

2. **Preparation state**

   * Don’t back-project cooked → raw; map to appropriate TPT.
   * Only impute via factors (retention/yield) when no prepared evidence exists; tag `derivation=imputed`, lower weight.

3. **Conflict resolution / rollup**

   * Tier sources (analytical > curated > survey > label > imputed).
   * Drop outliers; aggregate with **weighted median**.
   * Persist `min`, `max`, `n_sources` via provenance/flags (optional).

4. **Transform-aware mapping**

   * Use TPT identity (transforms + params) to match as-prepared foods.
   * Capture transform hints from labels into `mapping.jsonl.llm_suggestion`.

---

## Acceptance Checks (must pass to ship profiles)

* **Mapping yield**: ≥ threshold (per source type) for `node_id` non-null among foods with nutrients.
* **Core coverage**: energy/protein/fat/carb/sugar/fiber present for ≥ Y% of mapped foods.
* **Energy reconciliation**: >90% of cases within ±8%.
* **No unit/basis leaks** among `used=1`.
* **Outliers**: excluded share per nutrient ≤ Z%.
* **Provenance**: every profile has ≥1 non-imputed row unless marked `fallback_impute`.

---

## LLM Prompt & Minimal Orchestration (POC)

**Candidate generation (cheap):**

* Query `graph.db.search_fts` with the food label; take top 20 (taxon + TP + TPT).
* Pass those **names only** (no IDs) to the LLM alongside the **transforms/parts dictionaries**.

**Prompt shape (succinct):**

* “Given this food name: ‘…’, pick part + transforms; emit JSON with `part_id`, `transforms`, optional `attributes`, and `novelty` if a needed part/transform is missing. Use only these **allowed** `parts` and `transforms` unless novelty is obvious. If it maps directly to one of these candidate names, set `maps_to_name`.”

**Post-LLM rules:**

* If `maps_to_name` present → resolve to TP/TPT by name (or your `signature`), set `node_id`.
* Else if `(part + transforms)` equals an existing TPT identity → resolve via `(taxon_id, part_id, identity_hash)`.
* Else → `node_id:null` + `proposed_identity` for human review.

> **Yes, I can produce these JSON rows** given your identity structure. This stays “non-tool, non-reasoning” on the LLM side; your runner orchestrates I/O.

---

## Phases & Deliverables (with evidence specifics)

**Phase 0 — Foundations**

* Seed `nutrient_def.json` (INFOODS core), `nutrient_alias_map.json`.
* Add `uq_tpt_identity` (and optional `signature` column) to pack.

**Phase 1 — Evidence Ingestion (files only)**

* Emit `<source>/foods.jsonl`, `nutrients.jsonl` unchanged from source (except light normalization of text encodings).
* Write `source.json`.

**Phase 2 — Mapping to Nodes**

* Generate `mapping.jsonl` via (`search_fts` → LLM) + human review for `node_id:null` rows.
* **Policy:** accept `node_id` only when `confidence ≥ threshold` (from `rollup_config`).

**Phase 3 — Profiles Build**

* Run `profiles:compute` to fill `nutrition_profile_*` in `app.db` (attach `graph.db`, stream evidence files).

**Phase 4 — QA & Acceptance**

* Run the acceptance checks and emit a compact report in `evidence/<source>/logs/acceptance.json`.

**Phase 5 (optional) — %DV/Portions**

* `daily_value_table`, `portion_definition` (UI only).

**Phase 6 (optional) — Imputation Factors**

* `retention_factor.jsonl`, `yield_factor.jsonl` (used only when mapping lacks prepared foods).

---

## Common Queries (unchanged mental model)

* **Get profile for a node** → `nutrition_profile_current(node_id, nutrient_id)`.
* **Explain value** → join to `nutrition_profile_provenance` (weights, inclusions/exclusions).
* **Family rollup** → use ontology closures (`taxon_ancestors`, `part_ancestors`) and re-aggregate across descendants.

---

## Data Quality & Governance (fits Git)

* Evidence rows are **immutable** once committed (fixes via new source versions).
* `mapping.jsonl` is your **curation ledger**; PRs cleanly show deltas (`node_id` filled, new candidates).
* Rollups are **idempotent**; keep `rollup_config.json` versioned.
* Bright line for **imputed** vs measured (weights + flags).

---

## Tiny Worked Example (as before, now with files)

* `fdc-2024-09/foods.jsonl` → Greek yogurt, bacon.
* `nutrients.jsonl` → PROCNT=10.2 g/100 g for yogurt; FAT=42 g/100 g for bacon.
* `mapping.jsonl` → Greek yogurt maps to existing TPT; bacon maps to TPT with `cure+smoke`.
* `profiles:compute` → weighted median → stored into `nutrition_profile_current` with provenance and flags.

---

## Build Commands (POC CLI shape)

* `graph:pack` → runs Stage F to produce `graph.db` (no change to your current runner).
* `evidence:ingest <source>` → writes `<source>/{source.json,foods.jsonl,nutrients.jsonl}`.
* `evidence:map <source>` → reads foods, hits `search_fts`+LLM, writes `mapping.jsonl` (leaves `node_id:null` for candidates).
* `profiles:compute` → attaches `graph.db`, streams all `evidence/**`, writes/refreshes `nutrition_profile_*` in `app.db`.
* `profiles:report` → acceptance metrics JSON.

---

## What we are **not** doing (on purpose, POC discipline)

* No background services; no heavy ETL warehouse.
* No new ID scheme — we reuse your packed IDs.
* No hard dependency on a second database for evidence; files in Git suffice.
* No complex “semantic signatures” beyond the (optional) `tpt_nodes.signature` helper.

---

## What details are **still missing / need decisions**

1. **Exact LLM model + prompt**

   * We sketched the I/O; finalize the minimal prompt, temperature, and top-K candidate count from FTS (10? 20?).
   * Decide confidence scoring formula (LLM score × FTS similarity).

2. **Thresholds**

   * `confidence_threshold_for_mapping` default (0.7?), outlier rule (MAD k=3 vs P5–P95), % caps for imputation per nutrient.

3. **Liquid handling**

   * Whether to treat **per 100 ml** as co-primary for display while profiles remain per 100 g; finalize density policies and uncertainty flags.

4. **Energy reconciliation policy**

   * Exact macro → kcal factors and tolerance (±8% suggested); decide nutrients included (alcohol? polyols?).

5. **New ontology proposals path**

   * Where to record `proposed_identity` → do we write a **candidate JSONL** the ontology build can read to create new TPTs (behind a flag) or do we gate via manual edits only?

6. **%DV tables**

   * Jurisdictions (US/EU/CA/…) and years to seed; or defer entirely for POC.

7. **Imputation tables**

   * Source(s) and minimal subset to seed (e.g., USDA Retention Factors core vitamins).

8. **Where to store profiles**

   * Keep in `app.db` (recommended) or append to `graph.db` (single-file app)? Pick one to avoid ambiguity.

9. **Performance knobs**

   * Batch sizes for streaming JSONL → SQLite inserts; indexes to create/drop during load for speed.

---

### Bottom line

This version bakes the **simple, file-first evidence build** into your existing workflow, uses your **current TP/TPT IDs**, and adds only what’s necessary: a JSONL **mapping ledger**, a **minimal LLM assist**, and a deterministic **profiles step**. It stays POC-friendly, fast, and Git-reviewable—while preserving the full rigor of nutrient normalization, transform-aware mapping, and provenance you wanted.
