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
data/
  evidence/
    _registry/
      nutrient_def.json            # canonical nutrient ids/units used by evidence builds
      nutrient_alias_map.json      # source→canonical nutrient name mapping
      rollup_config.json           # merge/precedence rules for profiles
    <source>-<version>/            # e.g., fdc-2024-09, ciqual-2020
      source.json                  # metadata: {name, version, url, retrieved_at, license, checksum}
      foods.jsonl                  # one row per source food (verbatim-ish)
      nutrients.jsonl              # food × nutrient records
      mapping.jsonl                # LLM/heuristic mapping results (one row per food)
      logs/                        # acceptance, coverage, QA reports (optional)
```

**New ETL2 utilities (POC, outside Stage F)**

```
etl2/
  evidence/
    map.py         # builds mapping.jsonl from foods.jsonl + graph search + LLM
    profiles.py    # computes nutrition_profile_* tables from evidence/* → SQLite
```

---

## Nutrient ID Strategy: INFOODS/EuroFIR as Canonical Standard

> **Critical Decision Point**: This is exactly where picking the "right" IDs will save you years of churn.

### Recommendation

Use **INFOODS/EuroFIR component tagnames** as your **primary nutrient IDs**, and treat everything else (USDA FDC numeric IDs, SR-Legacy nutrient numbers, CNF/UK codes, label fields) as **aliases** in a cross-walk.

**Why:**

* **International + long-lived.** EuroFIR's component identifiers are explicitly **based on INFOODS tagnames** and have been harmonized; this is the closest thing our field has to a neutral, cross-database standard.
* **Cross-walks already exist (or are easy).** FDC exposes `nutrient_nbr` values that line up with SR-Legacy nutrient numbers; EuroFIR has published SR-to-EuroFIR component mappings—so you can bridge **FDC → SR-Legacy → INFOODS/EuroFIR** with high coverage.
* **Many national FCDBs align around INFOODS/EuroFIR.** That makes it easier to add the UK dataset (McCance & Widdowson), Canada's CNF, AUSNUT, etc., without inventing one-off keys.

### What Others Use (Practically)

* **USDA FDC**: internal `nutrient.id` plus `nutrient_nbr` (the SR-Legacy code many tools still recognize). This makes FDC→SR mapping straightforward.
* **SR-Legacy**: the classic **nutrient numbers** (e.g., 203 protein, 204 fat, 208 energy), still referenced widely.
* **EuroFIR member datasets (e.g., UK)**: local codes but curated with **EuroFIR component identifiers** that tie back to INFOODS.
* **CNF (Canada)**: national codes; per-food coverage up to **~152 nutrients**—roughly on par with SR-Legacy breadth.

### "Greatest Depth?" (Who Has the Most Nutrients)

No single general-purpose database wins across all foods. **FDC/SR-Legacy** tops out around **~150 components** per food; **CNF** similarly reports **up to ~152**; the **UK** dataset varies by food; and specialized resources (e.g., EuroFIR partners, phytochemical databases) can be deeper for specific compound classes. In short: **FDC is broad and current for the U.S., but not uniquely deepest** across every nutrient class.

### Implementation Strategy for Our Stack

1. **Canon = INFOODS/EuroFIR tag**
   Keep our current INFOODS IDs (e.g., `ENERC_KCAL`, `PROT`, `FAT`, etc.) as the primary key in our ontology.

2. **Alias columns for cross-walks**
   For each tag, store:
   ```json
   "aliases": { 
     "sr_legacy": [203], 
     "fdc_nutrient_ids": [1003], 
     "eurofir_id": "PROT", 
     "label_name": "Protein" 
   }
   ```
   This future-proofs joins and keeps our UI/ETL clean.

3. **Build the automatic bridge**
   * From **FDC nutrient.csv**, use `nutrient_nbr` → **SR-Legacy**
   * Map **SR-Legacy** → **INFOODS/EuroFIR** using:
     * Our current tag list (high-confidence core)
     * EuroFIR SR reports (to catch long tail)
   * Flag leftovers for manual curation (polyphenols, rare lipids, added/intrinsic split nutrients, etc.)

4. **Units & expression**
   Follow INFOODS/EuroFIR guidance: tags are identifiers; **units are separate** and standardized (kcal vs kJ, g/mg/µg), which simplifies normalization.

5. **Coverage plan**
   Our current INFOODS set is strong for macro + label + common micros. Expect to **add tails** for: amino acid detail, full FA isomers, sugar alcohols, bioactives. INFOODS/EuroFIR provide canonical identifiers for most of these when we need them.

### Next Steps

1. **Auto-generate FDC→INFOODS cross-walk** using the SR-Legacy hop
2. **Update nutrient registry** to include comprehensive alias mappings
3. **Implement automatic nutrient mapping** in the evidence pipeline
4. **Flag gaps/duplicates** for manual curation

### Immediate Implementation Plan

**Phase 1: Fix Current Nutrient Loading (Immediate)**
- ✅ Fix data type mismatch in FDC ID comparison (completed)
- 🔄 Test nutrient loading with current fallback map
- 📝 Document current nutrient coverage

**Phase 2: Build Comprehensive Mapping (Next Sprint)**
- 🔧 Create script to parse FDC `nutrient.csv` and extract `nutrient_nbr` mappings
- 🔧 Map SR-Legacy numbers to INFOODS tags using existing registry + EuroFIR reports
- 🔧 Update `nutrients-infoods.json` with comprehensive alias mappings
- 🔧 Remove hardcoded fallback map from evidence mapping script

**Phase 3: Enhanced Coverage (Future)**
- 🔧 Add missing nutrients from EuroFIR SR reports
- 🔧 Implement manual curation workflow for unmapped nutrients
- 🔧 Add support for specialized nutrient classes (amino acids, fatty acids, etc.)

**Expected Outcome**: Move from ~8 nutrients per food to ~50-100+ nutrients per food with proper international standardization.

---

## Evidence File Contracts (POC JSONL/JSON)

### `nutrient_def.json` (global)

INFOODS-first registry with comprehensive alias mappings.

```json
[
  {
    "nutrient_id": "PROCNT",
    "name": "Protein",
    "category": "macro",
    "canonical_unit": "g",
    "precision": 1,
    "is_energy": false,
    "notes": "Total protein",
    "aliases": {
      "sr_legacy": [203],
      "fdc_nutrient_ids": [1003],
      "eurofir_id": "PROT",
      "label_name": "Protein"
    }
  },
  {
    "nutrient_id": "ENERC_KCAL",
    "name": "Energy (kcal)",
    "category": "macro",
    "canonical_unit": "kcal",
    "precision": 0,
    "is_energy": true,
    "aliases": {
      "sr_legacy": [208],
      "fdc_nutrient_ids": [1008],
      "eurofir_id": "ENERC_KCAL",
      "label_name": "Calories"
    }
  },
  {
    "nutrient_id": "FAT",
    "name": "Total lipid (fat)",
    "category": "macro",
    "canonical_unit": "g",
    "precision": 1,
    "is_energy": false,
    "aliases": {
      "sr_legacy": [204],
      "fdc_nutrient_ids": [1004],
      "eurofir_id": "FAT",
      "label_name": "Total Fat"
    }
  }
]
```

### `nutrient_alias_map.json` (global)

**DEPRECATED** - Alias mappings are now embedded in `nutrient_def.json` for better maintainability and single source of truth.

This file can be auto-generated from `nutrient_def.json` if needed for backward compatibility:

```json
{
  "fdc": {
    "1003": "PROCNT",
    "1004": "FAT", 
    "1005": "CHOCDF",
    "1008": "ENERC_KCAL",
    "1051": "WATER",
    "1079": "FIBTG",
    "1093": "NA",
    "1087": "CA"
  },
  "sr_legacy": {
    "203": "PROCNT",
    "204": "FAT",
    "205": "CHOCDF", 
    "208": "ENERC_KCAL"
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

One line per external food (immutable evidence row). Minimal shape:

```json
{"food_id":"fdc:12345","name":"Greek yogurt, plain, nonfat","brand":null,"lang":"en","labels":["usda"],"country":"US"}
{"food_id":"fdc:789012","name":"Bacon, cooked, pan-fried","brand":null,"lang":"en","labels":["usda"],"country":"US"}
```

Required: `food_id`, `name`. Optional: `brand`, `lang`, `labels[]`, `country`.

### `<source_id>/nutrients.jsonl`

One line per (food × nutrient). Units/basis **as provided**.

```json
{"food_id":"fdc:12345","nutrient_id":"kcal","value":59,"unit":"kcal/100g","basis":"per_100g","method":"lab|panel|imputed","source_detail":"FDC_2024"}
{"food_id":"fdc:12345","nutrient_id":"PROCNT","value":10.2,"unit":"g/100g","basis":"per_100g","method":"lab","source_detail":"FDC_2024"}
{"food_id":"fdc:789012","nutrient_id":"FAT","value":42,"unit":"g/100g","basis":"per_100g","method":"lab","source_detail":"FDC_2024"}
```

Required: `food_id`, `nutrient_id`, `value`. Units should be normalized via `_registry/nutrient_def.json` or flagged in QA.

### `<source_id>/mapping.jsonl`

**One row per food in `foods.jsonl`.** POC-simple, graph-aware:

```json
{
  "food_id": "fdc:12345",
  "node_kind": "tpt",                      // 'taxon' | 'tp' | 'tpt'
  "node_id": "tpt:bos_taurus:milk:yogurt", // graph.db ref_id; null => candidate
  "identity_json": {                       // always present (source of truth)
    "taxon_id": "tx:animalia:...:bos:taurus",
    "part_id": "part:milk",
    "transforms": [
      {"id":"tf:ferment","params":{"starter":"lactobacillus"}},
      {"id":"tf:strain","params":{"strain_level":10}}
    ]
  },
  "confidence": 0.86,
  "rationales": ["name match + synonyms", "strain_level bucketed ≥7% => greek_style"],
  "new_taxa": [],                          // array of {suggest_id?, display_name, parent_id, rank, notes}
  "new_parts": [],                         // array of {suggest_id?, name, parent_id?, category}
  "new_transforms": [],                    // array of {id or suggest_id, params_schema?, notes}
  "warnings": ["unit mismatch in source panel"]
}
```

* **If `node_id` is null** → treat as **candidate ontology additions** (review required).
* `node_kind` disambiguates which table the `node_id` targets (`nodes`, `taxon_part_nodes`, `tpt_nodes`).
* `identity_json` is the canonical path you can always rebuild a TPT from (even if `node_id` is unset).

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

## Mapping Workflow (POC)

**Goal:** quick & dirty mapping of source foods → graph identity, plus surfaced ontology gap proposals.

**Steps**

1. **Compile ontology** (unchanged): `pnpm etl2:run` → `etl2/build/database/graph.dev.sqlite`.
2. **Map**: `pnpm evidence:map`

   * Uses `search_fts` in the graph DB for string matching.
   * Prompt LLM (no tools) to normalize to `{taxon_id, part_id, transforms[]}` and choose `node_kind`.
   * Write one `mapping.jsonl` per source directory.
3. **Profiles**: `pnpm profiles:compute`

   * Join `nutrients.jsonl` with `mapping.jsonl` (only those with `node_id` set, POC).
   * Compute current rollup and provenance tables into the **same** SQLite.

**Heuristics (POC)**

* Prefer exact `name_overrides` and TP synonyms when present.
* If transform params map to bucket rules (`param_buckets.json`), snap them before identity.
* Confidence threshold: default accept ≥0.70; below → leave `node_id=null`, keep `identity_json` as proposal.

**Safety rails**

* Reject LLM outputs that reference unknown `tf:` / `part:` / `tx:` ids (send to `warnings`).
* Emit `new_*` proposals only when `node_id=null`.

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

**Tables (POC DDL)**

```sql
-- Current, denormalized for reads
CREATE TABLE IF NOT EXISTS nutrition_profile_current (
  node_kind   TEXT NOT NULL,                 -- 'tpt'|'tp'
  node_id     TEXT NOT NULL,                 -- ref to tpt_nodes.id or taxon_part_nodes.id
  nutrient_id TEXT NOT NULL,
  value       REAL NOT NULL,
  unit        TEXT NOT NULL,
  source_id   TEXT NOT NULL,                 -- e.g., 'fdc-2024-09'
  updated_at  TEXT NOT NULL,
  PRIMARY KEY (node_kind, node_id, nutrient_id)
);

-- Provenance ledger (append-only)
CREATE TABLE IF NOT EXISTS nutrition_profile_provenance (
  id            TEXT PRIMARY KEY,            -- ulid/uuid
  node_kind     TEXT NOT NULL,
  node_id       TEXT NOT NULL,
  nutrient_id   TEXT NOT NULL,
  value         REAL NOT NULL,
  unit          TEXT NOT NULL,
  food_id       TEXT NOT NULL,               -- back to evidence row (e.g., fdc:12345)
  source_id     TEXT NOT NULL,               -- 'fdc-2024-09'
  mapping_conf  REAL,                        -- copy of mapping.confidence
  method        TEXT,                        -- lab|panel|imputed
  captured_at   TEXT,                        -- from source.json or file timestamp
  inserted_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_npp_node ON nutrition_profile_provenance(node_kind, node_id);
```

**Rollup policy (POC)**

* Keep **latest by `source_id` precedence** (defined in `_registry/rollup_config.json`) in `nutrition_profile_current`.
* Always append full provenance.

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

## Build Commands & Scripts (POC)

**Root `package.json` (new)**

```json
{
  "scripts": {
    "evidence:map": "python3 etl2/evidence/map.py --graph etl2/build/database/graph.dev.sqlite --evidence data/evidence",
    "profiles:compute": "python3 etl2/evidence/profiles.py --graph etl2/build/database/graph.dev.sqlite --evidence data/evidence --out etl2/build/database/graph.dev.sqlite"
  }
}
```

**`turbo.json` (optional cache)**

```json
{
  "tasks": {
    "evidence:map": {
      "inputs": ["data/evidence/**", "etl2/evidence/**", "etl2/build/database/graph.dev.sqlite"],
      "outputs": ["data/evidence/**/mapping.jsonl"]
    },
    "profiles:compute": {
      "inputs": ["data/evidence/**", "etl2/evidence/**", "etl2/build/database/graph.dev.sqlite"],
      "outputs": ["etl2/build/database/graph.dev.sqlite"]
    }
  }
}
```

**Commands**

* `graph:pack` → runs Stage F to produce `graph.db` (no change to your current runner).
* `evidence:ingest <source>` → writes `<source>/{source.json,foods.jsonl,nutrients.jsonl}`.
* `evidence:map <source>` → reads foods, hits `search_fts`+LLM, writes `mapping.jsonl` (leaves `node_id:null` for candidates).
* `profiles:compute` → attaches `graph.db`, streams all `evidence/**`, writes/refreshes `nutrition_profile_*` in `app.db`.
* `profiles:report` → acceptance metrics JSON.

---

## API Integration

* No changes required for core routes—the API keeps reading the same DB.
* Optional future routes:

  * `/profiles/:node_id` → current nutrient panel
  * `/profiles/:node_id/provenance` → ledger
  * `/evidence/coverage` → % mapped per source

---

## QA & Review Loops

* **Schema checks**: validate all evidence JSONL with simple JSON Schemas (fast fail).
* **Mapping acceptance**:

  * accept if `confidence ≥ threshold` AND identity ids exist in graph DB.
  * else: keep `node_id=null`, route to review queue (just `logs/pending.csv` in POC).
* **Ontology proposals** (`new_taxa`, `new_parts`, `new_transforms`):

  * accumulate into `data/evidence/_proposals/{taxa,parts,transforms}.jsonl`
  * human review → PR → merged into `data/ontology/**`
  * next build resolves future `node_id`s automatically.

---

## LLM Usage

* **Model**: GPT-5 Thinking (non-tool, reasoning off) or Gemini 1.5 Pro (cost/speed trade).
* **Decoding**: temperature 0.2–0.3, max tokens ~600.
* **Output**: strict JSON; include `confidence`, `rationales`, and `new_*` arrays when applicable.
* **Guardrails**: reject if unknown ids, or if JSON invalid → log and skip.

---

## What we are **not** doing (on purpose, POC discipline)

* No background services; no heavy ETL warehouse.
* No new ID scheme — we reuse your packed IDs.
* No hard dependency on a second database for evidence; files in Git suffice.
* No complex “semantic signatures” beyond the (optional) `tpt_nodes.signature` helper.

---

## Open Questions / TBD

1. **Source precedence strategy** in `rollup_config.json` (per nutrient? global?).
2. **Unit harmonization rules** (e.g., per 100 g vs per serving; density assumptions).
3. **Language/locale handling** for matching (`lang` on foods, synonyms by locale).
4. **Limits/backoff** for LLM calls and caching of prompts/responses.
5. **When to attach to TP vs TPT** if transforms are ambiguous—POC rule?
6. **Acceptance threshold defaults** and per-source overrides.
7. **Minimal editor/reviewer workflow** for `_proposals/` (labels, owners).
8. **Exact LLM model + prompt**

   * We sketched the I/O; finalize the minimal prompt, temperature, and top-K candidate count from FTS (10? 20?).
   * Decide confidence scoring formula (LLM score × FTS similarity).

9. **Thresholds**

   * `confidence_threshold_for_mapping` default (0.7?), outlier rule (MAD k=3 vs P5–P95), % caps for imputation per nutrient.

10. **Liquid handling**

    * Whether to treat **per 100 ml** as co-primary for display while profiles remain per 100 g; finalize density policies and uncertainty flags.

11. **Energy reconciliation policy**

    * Exact macro → kcal factors and tolerance (±8% suggested); decide nutrients included (alcohol? polyols?).

12. **%DV tables**

    * Jurisdictions (US/EU/CA/…) and years to seed; or defer entirely for POC.

13. **Imputation tables**

    * Source(s) and minimal subset to seed (e.g., USDA Retention Factors core vitamins).

14. **Performance knobs**

    * Batch sizes for streaming JSONL → SQLite inserts; indexes to create/drop during load for speed.

---

### Bottom line

This version bakes the **simple, file-first evidence build** into your existing workflow, uses your **current TP/TPT IDs**, and adds only what's necessary: a JSONL **mapping ledger**, a **minimal LLM assist**, and a deterministic **profiles step**. It stays POC-friendly, fast, and Git-reviewable—while preserving the full rigor of nutrient normalization, transform-aware mapping, and provenance you wanted.

---

## Quick Start

```bash
# 1) Build ontology → graph DB
pnpm etl2:run

# 2) Map all evidence sources → mapping.jsonl
pnpm evidence:map

# 3) Materialize nutrient profiles into the same DB
pnpm profiles:compute

# 4) Run API/UI against that DB as usual
pnpm dev
```
