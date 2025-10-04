
# What nutrition data looks like “in the wild”

**Per-nutrient rows per food is the norm.** Most public datasets model a food with many nutrient records (one row per nutrient). USDA FoodData Central (FDC) does exactly this: the `food_nutrient` table stores the **amount of a nutrient per 100 g** of the food, along with unit, derivation and stats (min, max, median, etc.). 

**FDC data types** (Foundation Foods, SR Legacy, Branded, FNDDS) all surface nutrients as an array of `{nutrient, amount, unit, derivation…}` attached to a food, with the 100 g basis as the default expression for amounts. ([FoodData Central][1])

**Global tagging exists for nutrients.** FAO/INFOODS publishes a widely used registry of **component identifiers (tagnames)** (e.g., `ENERC_KCAL`, `PROCNT`, `FAT`, `CHOCDF`, `FIBTG`…), and their guidance standardizes reporting **per 100 g edible portion** (and per serving/household measures as needed). These tags are ideal as your canonical nutrient IDs. ([FAOHome][2])

**Regulatory/label ecosystems also align on a small core.** Even when values are given **per serving** (e.g., label/NFP or GDSN), the set is the same macro/micro family; you can convert to 100 g when serving size and density are available, while retaining the original basis for provenance. (INFOODS explicitly discusses per-100 g EP vs per serving conventions.) ([FAOHome][2])

**Preparation matters.** Sources often publish foods in raw and cooked states, and traditionally use **retention factors** to estimate vitamin/mineral losses on cooking; USDA’s retention-factor tables are commonly referenced in imputation workflows. ([intake.org][3])

> TL;DR: Expect to ingest a lot of “food × nutrient” rows (per 100 g by default), with varied derivations (analytical vs label-calculated) and preparation states. You don’t need to mirror any one source’s ontology to use them.

---

# Design goals (what we want)

* **Keep your food graph clean** (T, TP, TPT remain your source of truth).
* **Ingest any dataset** (FDC/CIQUAL/CoFID/brand/GDSN) as raw evidence, unchanged.
* **Normalize nutrients once**, using a global registry (INFOODS tags), plus robust units.
* **Attach provenance to evidence**, not to the graph nodes directly.
* **Roll up** evidence into **stable per-node nutrition profiles** (per 100 g EP by default), with clear conflict-resolution rules.
* **Be transform-aware** (TPT identity → “as prepared/as eaten” basis).

---

# Schemas (no code; contracts and relationships)

## 1) Canonical nutrient registry (global)

**`nutrient_def`**

* `nutrient_id` (PK) — use **INFOODS tagname** (e.g., `PROCNT`, `FAT`, `CHOCDF`, `FIBTG`, `ENERC_KCAL`).
* `name`, `category` (macro | vitamin | mineral | fatty_acid | amino_acid | other)
* `canonical_unit` (UCUM: `g`, `mg`, `µg`, `kcal`, `kJ`, `IU`…)
* `alt_units` (list; optional) + **conversion** metadata (e.g., `kcal↔kJ`, `IU↔µg` where science allows).
* `notes` (definition/scoping, e.g., “available carbohydrate by difference”).

**`nutrient_alias_map`**

* Maps **source-specific identifiers** → `nutrient_id`.

  * Examples: FDC `nutrient.number=1003` → `PROCNT`; `1004` → `FAT`; `1005` → `CHOCDF`; `1008` → `ENERC_KCAL`. 
  * INFOODS already matches your canonical IDs. ([FAOHome][2])

**Why INFOODS?** It’s internationally used and explicitly designed for cross-database mapping, not just US-centric. ([FAOHome][2])

## 2) Sources, foods, and raw evidence

**`nutrition_source`**

* `source_id` (PK), `name`, `version`, `license`, `citation`, `ingest_date`, `kind` (foundation | branded | survey | lab | gdsn | other)
* Optional **quality defaults** (e.g., “analytical preferred over label” per source subtype). ([FoodData Central][1])

**`external_food`**

* `(source_id, external_food_id)` (PK)
* `label` (source name), `brand` (if any), `data_type` (FDC: Foundation/SR Legacy/Branded/FNDDS), `description`
* `state` (raw | cooked | dried | canned | “as packaged” | other)
* `prep_method` (free-text + mapping to your **tf:** transforms when feasible)
* `edible_portion_note` (EP basis)
* `serving_size_unit`, `serving_size_amount` (if present)
* `density_g_per_ml` (optional; helps convert serving → per 100 g)

**`external_food_nutrient`**

* `(source_id, external_food_id, nutrient_id)` (PK) — **one row per nutrient**.
* `amount` (numeric) — **as provided**; carry `unit` (UCUM).
* `basis` (per_100g | per_100ml | per_serving | per_100kcal | per_100kJ)
* `derivation` (analytical | calculated | label | imputed | recipe), `method_code`/`lab_method` if available, `sample_n`, `std_error`, `min`, `max`, `median`.

  * FDC documents these fields at `food_nutrient` level (amount per 100 g, unit, derivation, stats). 

> This is your **immutable raw evidence** layer. No coercion beyond unit/basis normalization.

## 3) Mapping evidence to your graph

**`external_food_mapping`**

* `(source_id, external_food_id)` → `graph_node_id` (TP or TPT), `node_type` (TP|TPT), `confidence` (0–1), `method` (rules | FTS | human curation), `notes`.
* Allow **many→one** (multiple source foods mapped to one node) and **one→many** (ambiguous, mark low confidence).

**Best practice:** Map **like-with-like**:

* Raw Apple (TP) ⇄ raw apple entries.
* “Butter, salted” (TPT butter) ⇄ butter records.
* “Yogurt, Greek, plain” ⇄ strained-yogurt TPTs (your identity path knows it’s strained).

## 4) Normalized profiles (rollups) for graph nodes

**`nutrition_profile_current`**

* `(graph_node_id, nutrient_id)` (PK)
* `amount_per_100g` (canonical unit), `amount_basis` (usually per_100g EP), `method` (weighted_median | meta_mean | choose_best_source), `n_sources`, `last_updated`.
* `provenance_summary` (compact string like: “FDC Foundation (3), FNDDS (1), CIQUAL (1)”)

**`nutrition_profile_history`** (optional)

* Snapshots over time for auditability.

**`nutrition_profile_provenance`** (optional, drill-down)

* Link each `(graph_node_id, nutrient_id)` to the **subset of external rows** that contributed, with weights and outlier flags.

---

# Ingestion & normalization rules

**1) Units & basis**

* Canonicalize to **INFOODS + UCUM** units. Keep original units alongside canonical.
* Prefer **per 100 g edible portion** as your **default basis**. Convert from per serving/100 ml where possible; otherwise store natively and mark `basis`. (INFOODS guidance explicitly frames 100 g EP as a standard expression.) ([FAOHome][2])
* Energy: support both `ENERC_KCAL` and `ENERC_KJ`, define fixed conversion.

**2) Preparation state**

* If source food is cooked, **do not back-project to raw**. Treat it as a distinct mapped node (ideally a TPT whose identity path includes the relevant **tf:cook**). If needed, apply **retention factors** only in a transparent imputation pipeline (tagged as `derivation=imputed`). ([intake.org][3])

**3) Conflict resolution / rollup**

* **Tier sources** (e.g., analytical > curated foundation > survey > label > inferred).
* Aggregate per `(node, nutrient)` using **robust stats**:

  * Drop extreme outliers (MAD/percentile trims).
  * Compute **weighted median** (weights by source tier, recency, sample_n).
  * Keep `min`, `max`, `n_sources`.
* Always keep the **raw evidence**—profiles are reproducible summaries.

**4) Transform-aware mapping**

* Use your **identity path** to map “as prepared”. Example:

  * `tpt:…:yogurt` (has `tf:ferment` + `tf:strain`) ⇄ foods named “Greek/strained yogurt”.
  * `tpt:…:bacon` (cured+smoked) ⇄ cured smoked pork belly entries.
* If a source food’s label implies transforms, record that in `external_food.prep_method` and/or a transform-like annotation to guide mapping.

---

# Why this avoids “nutrition evidence” glued to nodes

* Your nodes (TP/TPT) stay **ontology-clean**. Provenance lives one hop away in `external_food_*`.
* You can **roll up** across all children mapped to a node (or even across a family) without duplicating evidence rows.
* Switching profile methodology later doesn’t mutate source data or the ontology; you just recompute `nutrition_profile_*`.

---

# Minimum viable fields cheat-sheet (what to insist on from any source)

* For every external food: **human label**, **basis** (per 100 g/serving), **state/prep**, and **portion/serving info** if basis ≠ 100 g.
* For every nutrient row: **nutrient identifier**, **amount**, **unit**, **derivation** (analytical/calculated/label), and any **variance stats** if provided.

  * FDC provides all of these in `food_nutrient` including derivation and stats; amounts are per 100 g. 
* Map all nutrient identifiers to **INFOODS tags**. ([FAOHome][2])

---

# Open considerations (worth deciding up front)

* **Jurisdictional DVs/NRVs:** If you’ll surface %DV, keep a small table keyed by market/regulation (US FDA, EU). (Not required for ingestion.)
* **Edible portion normalization:** Some sources embed in the definition; keep an `EP_flag` and a short note.
* **Density estimation:** Labels often give per serving; you’ll need density or drained‐weight data to convert confidently (store uncertainty if estimated).
* **Families & transforms in profiles:** You can also compute **family-level medians** (e.g., “hard cheeses”) by aggregating over descendants using your part/taxon closures.

---

## Why this is compatible with multiple public datasets

* **USDA FoodData Central** (Foundation/SR Legacy/Branded/FNDDS) → nutrients per 100 g as `food_nutrient` rows with derivations and stats; perfect for `external_food_*`. 
* **INFOODS** → gives you the stable **nutrient ID system** (tagnames) and reinforces 100 g EP reporting. ([FAOHome][2])
* **Others (CIQUAL, CoFID, etc.)** → follow similar per-food, per-nutrient shapes focused on 100 g conventions, so they’ll slide into the same evidence schema (INFOODS tags smooth the mapping). ([FAOHome][2])

---

## How this ties back to your graph

* **TP nodes (normally eaten raw parts)** get profiles by direct mapping (e.g., Apple flesh).
* **TPT nodes (processed products)** get profiles that already reflect transforms (e.g., bacon, yogurt, cheddar), because you map them to matching prepared foods in sources.
* **Up-the-tree rollups** (e.g., “all hard cheeses”) use your **part_ancestors** + taxon closures to summarize over descendants.

[1]: https://fdc.nal.usda.gov/data-documentation "Data Documentation | USDA FoodData Central"
[2]: https://www.fao.org/fileadmin/templates/food_composition/documents/1nutrition/Conversion_Guidelines-V1.0.pdf "Microsoft Word - Conversion Guidelines Nov2012-4-clean.docx"
[3]: https://www.intake.org/resource/usda-table-nutrient-retention-factors-release-6?utm_source=chatgpt.com "USDA Table of Nutrient Retention Factors - Release 6"


---

Perfect—here’s the “nutrition layer” spec you asked for: the exact tables/fields, semantics, and the roll-up logic to turn heterogeneous public datasets into clean, reproducible nutrition profiles for your TP/TPT nodes. No code, just contracts and examples.

---

# 0) Principles (recap)

* **Evidence lives off-graph.** External foods and their per-nutrient rows are ingested verbatim into an evidence layer; we never reshape the ontology to match a source.
* **One canonical nutrient vocabulary.** We adopt **INFOODS tagnames** (e.g., `PROCNT`, `FAT`, `CHOCDF`, `FIBTG`, `ENERC_KCAL`) as our stable `nutrient_id`. Everything maps to these.
* **Canonical basis = per 100 g EP.** We store/compute normalized amounts per 100 g **edible portion**. We also retain the native basis (per serving, per 100 ml, etc.) in evidence for provenance.
* **Transform-aware mapping.** TPT identity (e.g., cured+smoked) tells us which external cooked/prepared foods to map.
* **Rollups are reproducible views.** Profiles are computed from evidence with transparent weighting, outlier handling, and provenance.

---

# 1) Canonical nutrient registry

### `nutrient_def` (global dictionary)

* `nutrient_id` (PK, string) — INFOODS tagname (e.g., `PROCNT`, `FAT`, `ENERC_KCAL`, `VITA_RAE`).
* `name` (string) — human label (e.g., “Protein”, “Fat”, “Vitamin A (RAE)”).
* `category` (enum) — `macro | vitamin | mineral | fatty_acid | amino_acid | carbohydrate | sugar | organic_acid | other`.
* `canonical_unit` (UCUM string) — e.g., `g`, `mg`, `µg`, `kcal`, `kJ`, `IU` (only when appropriate).
* `precision` (int) — suggested decimal places for display.
* `is_energy` (bool) — true for `ENERC_KCAL`/`ENERC_KJ`.
* `notes` (text) — definition/boundaries (e.g., “Carbohydrate by difference”, “Vitamin A as µg retinol activity equivalents”).
* `parent_id` (nullable) — optional grouping (e.g., `FA` parent for fatty acids).

### `nutrient_alias_map`

* `source` (enum) — `fdc | ciqual | cof id | gdsn | brand | other`.
* `source_nutrient_key` (string) — the source’s identifier (number, code, or name).
* `nutrient_id` (FK → `nutrient_def`).
* `unit_hint` (nullable) — if source is ambiguous; else null.
* `confidence` (0–1) — mapping confidence (1 for unambiguous canonical matches).
* `notes`.

*(This lets you plug in any dataset without expanding your nutrient vocabulary.)*

---

# 2) Source registry & raw evidence

### `nutrition_source`

* `source_id` (PK, string) — e.g., `fdc-2024-09`.
* `name` (string) — “USDA FoodData Central”, “CIQUAL 2020”, etc.
* `version` (string), `license` (string/URL), `citation` (text), `kind` (enum: `foundation | branded | survey | lab | gdsn | other`).
* `ingest_date` (date).
* `default_quality_tier` (int) — lower is better (e.g., 1 analytic foundation, 2 curated survey, 3 label).

### `external_food`

* `(source_id, external_food_id)` (PK) — the dataset’s native key.
* `label` (string) — human name from source.
* `brand` (nullable).
* `data_type` (enum) — e.g., FDC: `Foundation | SR_Legacy | Branded | FNDDS`; others: dataset-specific buckets.
* `state` (enum) — `raw | cooked | dried | fermented | canned | pickled | as_packaged | other`.
* `prep_method` (string) — free text + optional normalized tokens (e.g., `boiled`, `baked`, `smoked hot`). We don’t force tf-mapping here, but we **can** record hints for mapping.
* `edible_portion_flag` (bool) — whether values are explicitly on edible portion basis.
* `serving_size_amount` (nullable numeric), `serving_size_unit` (nullable UCUM).
* `household_measure` (nullable string) — “1 cup”, “1 slice” (for branded/label data).
* `density_g_per_ml` (nullable) — helpful for serving→100 g conversions in liquids.
* `country` (nullable), `lang` (nullable).
* `notes`.

### `external_food_nutrient`

* `(source_id, external_food_id, nutrient_id)` (PK).
* `amount` (numeric) — amount as provided by source.
* `unit` (UCUM string) — source unit, **before** normalization.
* `basis` (enum) — `per_100g | per_100ml | per_serving | per_package | per_100kcal | per_100kJ`.
* `derivation` (enum) — `analytical | calculated | label | imputed | recipe | unknown`.
* `method_code` (nullable) — source-specific lab method or calc code.
* `sample_n` (nullable int), `std_error` (nullable numeric), `min` (nullable), `max` (nullable), `median` (nullable).
* `quality_tier_override` (nullable int) — if a particular row deserves a better/worse tier than the source default.
* `last_updated` (date).

*(This is the immutable evidence layer: one row per food × nutrient, with native units and basis preserved.)*

---

# 3) Mapping evidence to graph nodes

### `external_food_mapping`

* `(source_id, external_food_id)` (PK).
* `graph_node_id` (string) — **TP** or **TPT** id.
* `node_type` (enum) — `TP | TPT`.
* `confidence` (0–1).
* `method` (enum) — `rules | text_match | ontology | human | hybrid`.
* `transform_hints` (json) — optional hints extracted from the source label/state (e.g., `{ "smoke": "cold", "cure": "dry" }`).
* `notes`.

**Mapping norms**

* Prefer **as-prepared** matches: e.g., “Greek yogurt, plain” ↔ TPT with `ferment+strain`.
* Avoid back-projecting cooked → raw; if necessary, tag imputation later.

---

# 4) Normalization scaffolding

### `unit_conversion`

* `from_unit` (UCUM), `to_unit` (UCUM), `nutrient_id` (nullable; most are generic).
* `factor` (numeric), `offset` (numeric, default 0).
* `notes`.
  *(Handle `kcal↔kJ`, `µg RAE↔IU` where appropriate and scientifically defensible.)*

### `basis_normalization_rule`

* `from_basis` → `to_basis` (we standardize to `per_100g`).
* `requires` (json) — what’s needed to convert (e.g., serving_size + density).
* `method` (enum) — `direct | density | EP_factor | cannot_convert`.
* `notes`.

*(We convert to per 100 g EP when possible; otherwise we’ll carry the native basis along and **exclude** those rows from certain rollups unless a safe conversion is available.)*

---

# 5) Computed profiles (stable per-node nutrition)

### `nutrition_profile_current`

* `(graph_node_id, nutrient_id)` (PK).
* `amount_per_100g` (numeric, canonical unit from `nutrient_def`).
* `basis` (enum) — typically `per_100g`.
* `method` (enum) — `weighted_median | weighted_mean | choose_best | fallback_impute`.
* `n_sources` (int) — number of **distinct external foods** contributing.
* `n_rows` (int) — total evidence rows contributing.
* `last_recomputed` (timestamp).
* `provenance_summary` (string) — compact, human-readable e.g., “FDC Foundation×3, FNDDS×1, CIQUAL×1”.
* `flags` (json) — diagnostics (e.g., “high variance”, “basis_mixed_filtered”).

### `nutrition_profile_provenance`

* `(graph_node_id, nutrient_id, source_id, external_food_id)` (compound PK).
* `weight` (numeric) — the weight assigned after QC/tiering.
* `used` (bool) — true if included post-outlier filter; false if excluded.
* `reason_excluded` (nullable string) — e.g., “outlier_high”, “basis_not_convertible”.

### `nutrition_profile_history` (optional)

* Snapshots of `nutrition_profile_current` for audit/versioning.

---

# 6) Roll-up algorithm (configurable, deterministic)

**Goal:** For each `(graph_node_id, nutrient_id)`, compute a single normalized value, reproducible from evidence.

**Defaults (tunable):**

1. **Collect candidates**

   * Pull all `external_food_nutrient` joined via `external_food_mapping` to the node (TP/TPT).
   * Filter to rows that can be normalized to **per 100 g** with canonical unit. If not convertible, keep as **eligible but excluded** (for diagnostics).

2. **Normalize**

   * Map `nutrient_id` via `nutrient_alias_map`.
   * Convert `unit` → `canonical_unit` using `unit_conversion`.
   * Convert `basis` → `per_100g` using `basis_normalization_rule` (serving size, density, EP flags).

3. **Weighting**

   * Assign a **quality tier** per row: by source default, overridden by row if present.
   * Base weight = `tier_weight` (e.g., 1.0 for analytical foundation, 0.7 for curated/survey, 0.5 for label, 0.3 for imputed).
   * Multiplied by `log(1 + sample_n)` if `sample_n` exists.
   * Optional **recency decay**: multiply by `exp(-λ * age_years)` for branded/rapidly changing products; skip for canonical commodities.

4. **Outlier handling**

   * Compute robust center (median) and dispersion (MAD or IQR).
   * Exclude rows beyond a threshold (default: **outside [P5, P95]** or **> 3× MAD**). Mark `reason_excluded`.

5. **Aggregate**

   * Default aggregator: **weighted median** (resists skew from uneven label data).
   * Tie-breaker: weighted mean among the middle 50% of weighted mass.

6. **Provenance & flags**

   * Record `n_sources`, `n_rows`.
   * Compute flags like `high_variance` (IQR/median > threshold), `basis_mixed_filtered` (had to exclude per-serving rows), etc.
   * Store compact `provenance_summary`.

**Policy switch:** `method=choose_best` for nutrients where one dataset is authoritative (e.g., specific amino acid profiles from a lab compendium).

---

# 7) Transform-aware estimation (only when needed)

When no suitable prepared food exists:

* Use the node’s identity to **impute** from a related node plus standard factors:

  * **Cooking yields/retention factors** (water/fat changes; vitamin retention).
  * **Curing/brining salt uptake**.
* Tag such rows with `derivation=imputed` and lower weight (e.g., 0.3). Keep the factor tables separate:

  * `retention_factor` (per nutrient × process family).
  * `yield_factor` (mass basis changes by transform).
* This keeps the line between **measured** and **estimated** bright.

---

# 8) Rollups above the leaf (families & closures)

You can compute medians for **families** or **ancestry groups**:

* Use `part_ancestors` and `taxon_ancestors` to gather descendants of, say, `part:cheese:hard`.
* Aggregate **across nodes** (TP/TPT) using the same outlier/weight pipeline but **without** mixing per-serving rows that can’t be normalized.
* Store in optional `nutrition_profile_family` with `group_id` (e.g., family code) and the same fields as `nutrition_profile_current`.

---

# 9) Serving sizes & regulatory %DV (optional layer)

### `daily_value_table` (optional)

* `(jurisdiction, year)` → a set of `(nutrient_id, daily_value_amount, unit)`.
* Lets you compute %DV for a given market; keep separate from core profiles.

### `portion_definition` (optional)

* Node-specific or family-specific “typical portion” for UI (e.g., 30 g cheese).
* Never used to **store** nutrition; only for friendly conversions in apps.

---

# 10) Minimal examples (illustrative)

*(Abbreviated for readability; values are exemplary.)*

**`nutrient_def`**

* `PROCNT` | “Protein” | macro | `g` | 1 | false
* `FAT` | “Total fat” | macro | `g` | 1 | false
* `CHOCDF` | “Carbohydrate, by difference” | carbohydrate | `g` | 1 | false
* `FIBTG` | “Fiber, total dietary” | fiber | `g` | 1 | false
* `ENERC_KCAL` | “Energy” | macro | `kcal` | 0 | true

**`nutrition_source`**

* `fdc-2024-09` | “USDA FoodData Central” | 2024.09 | license… | `foundation` | ingest_date…

**`external_food`**

* `(fdc-2024-09, 123456)` → label: “Yogurt, Greek, plain, whole milk”, state:`fermented`, prep:`strained`, EP: true
* `(fdc-2024-09, 789012)` → label: “Bacon, cooked, pan-fried”, state:`cooked`, prep:`fried`, EP: true

**`external_food_nutrient`** (selected)

* (fdc-2024-09, 123456, `PROCNT`) → amount: 10.2, unit:`g`, basis:`per_100g`, derivation:`analytical`
* (fdc-2024-09, 123456, `ENERC_KCAL`) → 120, `kcal`, `per_100g`, `analytical`
* (fdc-2024-09, 789012, `FAT`) → 42.0, `g`, `per_100g`, `analytical`

**`external_food_mapping`**

* `(fdc-2024-09, 123456)` → `tpt:…:yogurt:greece_style` (node_type:`TPT`, confidence:0.95, method:`hybrid`)
* `(fdc-2024-09, 789012)` → `tpt:…:sus:belly:cured_smoked` (node_type:`TPT`, confidence:0.9)

**Computed `nutrition_profile_current`**

* `(tpt:…:yogurt…, PROCNT)` → 10.3 g/100 g, method:`weighted_median`, n_sources:4, n_rows:7
* `(tpt:…:bacon…, FAT)` → 41.5 g/100 g, method:`weighted_median`, n_sources:5, n_rows:9

---

# 11) Common queries (mental model)

* **Get the profile for a TPT:** look up `(graph_node_id, nutrient_id)` in `nutrition_profile_current`. If missing, recompute from `external_food_*` via mapping.
* **Get a family profile (e.g., hard cheeses):** gather descendant nodes via `part_ancestors` + roll up as above into `nutrition_profile_family`.
* **Explain this number:** join to `nutrition_profile_provenance` to list contributing external foods and their weights; optionally show exclusions and reasons.

---

# 12) Data quality & governance

* Always keep the **raw evidence immutable**.
* Make the rollup **idempotent**: same evidence + same config ⇒ same profiles.
* Track **config version** (weights, outlier thresholds) alongside profiles so you can rebuild and compare.
* Prefer **weighted medians** for robustness across mixed source qualities.
* Keep **imputed** values clearly marked and down-weighted.

---

# 13) Where this fits your ontology

* **TP nodes** (e.g., `tx:plantae:rosaceae:malus … + part:fruit`) map to raw commodity entries.
* **TPT nodes** map to prepared foods (identity path ≈ preparation), making nutrition **as eaten**.
* **Closures** (`part_ancestors`, `taxon_ancestors`) let you compute **category medians** (e.g., “all hard cheeses”) without baking any of that into the ontology itself.

---

# 14) Open knobs you can tune later

* Tier weights per source kind.
* Outlier thresholds (MAD vs IQR trims).
* Recency decay for branded.
* Jurisdictional DVs for UI %DV.
* Whether to store **per 100 ml** as co-primary basis for liquids (we still normalize to per 100 g for cross-category comparability).

---

awesome — here’s the “reference JSON schemas + ingestion contract” for the nutrition layer. it’s concise but complete enough that a new data partner (or an engineer) can wire a source end-to-end without guesswork.

---

# 1) Reference JSON Schemas (contracts, not executable code)

Below, every table is expressed as a schema *contract*: field → type → constraints → semantics. Types: `string | number | integer | boolean | enum | date | json`. Units use UCUM strings (`g`, `mg`, `µg`, `kcal`, `kJ`, `ml`).

## 1.1 Nutrient dictionary

### `nutrient_def`

* `nutrient_id` (string, PK) — **INFOODS tagname** (e.g., `PROCNT`, `FAT`, `CHOCDF`, `FIBTG`, `ENERC_KCAL`, `VITA_RAE`).
* `name` (string) — human label.
* `category` (enum) — `macro | vitamin | mineral | fatty_acid | amino_acid | carbohydrate | sugar | organic_acid | other`.
* `canonical_unit` (string, UCUM) — unit to which all evidence will be normalized for this nutrient.
* `precision` (integer, 0–6) — display precision.
* `is_energy` (boolean) — true only for `ENERC_KCAL`/`ENERC_KJ`.
* `parent_id` (string, nullable, FK→nutrient_def.nutrient_id) — optional grouping.
* `notes` (string, nullable).

### `nutrient_alias_map`

* `source` (enum) — `fdc | ciqual | cof id | gdsn | branded | other`.
* `source_nutrient_key` (string, PK with `source`) — the source’s ID or canonical field name.
* `nutrient_id` (string, FK→nutrient_def).
* `unit_hint` (string, UCUM, nullable) — only if the source is ambiguous or context-dependent.
* `confidence` (number, 0–1, default 1.0).
* `notes` (string, nullable).

---

## 1.2 Source registry & raw evidence

### `nutrition_source`

* `source_id` (string, PK) — e.g., `fdc-2024-09`.
* `name` (string).
* `version` (string) — dataset release label.
* `license` (string/URL).
* `citation` (string).
* `kind` (enum) — `foundation | branded | survey | lab | gdsn | other`.
* `ingest_date` (date).
* `default_quality_tier` (integer) — lower = better (e.g., 1 analytic, 2 curated, 3 label).
* `notes` (string, nullable).

### `external_food`

* `source_id` (string, FK→nutrition_source, PK part).
* `external_food_id` (string, PK part) — the source’s key.
* `label` (string) — source name.
* `brand` (string, nullable).
* `data_type` (string/enum) — source-specific category (e.g., FDC `Foundation | Branded | FNDDS`).
* `state` (enum) — `raw | cooked | dried | fermented | canned | pickled | as_packaged | other`.
* `prep_method` (string, nullable) — free text; we’ll derive transform hints separately.
* `edible_portion_flag` (boolean) — true if already EP-normalized.
* `serving_size_amount` (number, nullable).
* `serving_size_unit` (string, UCUM, nullable).
* `household_measure` (string, nullable) — “1 cup”, “1 slice”.
* `density_g_per_ml` (number, nullable).
* `country` (string ISO 3166-1 alpha-2, nullable).
* `lang` (string BCP-47, nullable).
* `notes` (string, nullable).

### `external_food_nutrient`

* `source_id` (string, PK part, FK).
* `external_food_id` (string, PK part, FK).
* `nutrient_id` (string, PK part, FK→nutrient_def).
* `amount` (number) — **as provided** by source, pre-normalization.
* `unit` (string, UCUM) — as provided.
* `basis` (enum) — `per_100g | per_100ml | per_serving | per_package | per_100kcal | per_100kJ`.
* `derivation` (enum) — `analytical | calculated | label | imputed | recipe | unknown`.
* `method_code` (string, nullable) — lab method/calculation code.
* `sample_n` (integer, nullable).
* `std_error` (number, nullable).
* `min` (number, nullable).
* `max` (number, nullable).
* `median` (number, nullable).
* `quality_tier_override` (integer, nullable).
* `last_updated` (date, nullable).

**Row-level invariant:** `(source_id, external_food_id, nutrient_id)` is unique.

---

## 1.3 Mapping evidence → graph nodes

### `external_food_mapping`

* `source_id` (string, PK part).
* `external_food_id` (string, PK part).
* `graph_node_id` (string) — **TP** or **TPT** id (your ontology id space).
* `node_type` (enum) — `TP | TPT`.
* `confidence` (number, 0–1).
* `method` (enum) — `rules | text_match | ontology | human | hybrid`.
* `transform_hints` (json, nullable) — e.g., `{ "smoke": "cold", "cure": "dry" }`.
* `notes` (string, nullable).

**Uniqueness policy:** A given `(source_id, external_food_id)` *may* map to multiple nodes, but rollups will only use mappings whose `confidence ≥ threshold` (default 0.7). Keep duplicates rare and justified.

---

## 1.4 Normalization scaffolding

### `unit_conversion`

* `from_unit` (string, UCUM, PK part).
* `to_unit` (string, UCUM, PK part).
* `nutrient_id` (string, nullable, FK) — null = general conversion; set when conversion is nutrient-specific (e.g., IU↔µg RAE).
* `factor` (number) — multiplicative factor.
* `offset` (number, default 0) — additive offset (rare).
* `notes` (string, nullable).

### `basis_normalization_rule`

* `from_basis` (enum) — see above.
* `to_basis` (enum) — **must be `per_100g`** in our pipeline.
* `requires` (json) — e.g., `["serving_size_amount","serving_size_unit"]`, `["density_g_per_ml"]`, `["edible_portion_flag"]`.
* `method` (enum) — `direct | density | EP_factor | cannot_convert`.
* `notes` (string, nullable).

---

## 1.5 Computed profiles

### `nutrition_profile_current`

* `graph_node_id` (string, PK part).
* `nutrient_id` (string, PK part, FK→nutrient_def).
* `amount_per_100g` (number) — canonical unit from `nutrient_def`.
* `basis` (enum) — typically `per_100g`.
* `method` (enum) — `weighted_median | weighted_mean | choose_best | fallback_impute`.
* `n_sources` (integer) — distinct external foods contributing.
* `n_rows` (integer) — total evidence rows used.
* `last_recomputed` (date/time).
* `provenance_summary` (string) — compact human string (“FDC Foundation×3; CIQUAL×1”).
* `flags` (json) — e.g., `{"high_variance": true, "basis_mixed_filtered": true}`.

### `nutrition_profile_provenance`

* `graph_node_id` (string, PK part).
* `nutrient_id` (string, PK part).
* `source_id` (string, PK part).
* `external_food_id` (string, PK part).
* `weight` (number) — post-QC weight used in aggregation.
* `used` (boolean) — false if filtered (e.g., outlier).
* `reason_excluded` (string, nullable) — `outlier_high | outlier_low | basis_unconvertible | duplicate_inferior | other`.

### `nutrition_profile_history` (optional)

* same columns as `nutrition_profile_current` + `profile_version` (integer) and `config_version` (string).

---

## 1.6 Optional helpers (kept separate)

### `daily_value_table`

* `jurisdiction` (enum) — `us | eu | ca | au | other`.
* `year` (integer).
* `nutrient_id` (FK).
* `daily_value_amount` (number).
* `unit` (UCUM).
* **PK:** `(jurisdiction, year, nutrient_id)`.

### `portion_definition`

* `graph_node_id` (string, PK).
* `portion_amount` (number).
* `portion_unit` (UCUM).
* `label` (string) — e.g., “1 slice”, “1 Tbsp”.
* `notes` (string, nullable).

### `retention_factor` (for imputation only)

* `process_code` (enum) — e.g., `boil | bake | fry | smoke_cold | smoke_hot | cure_dry | cure_wet | ferment`.
* `nutrient_id` (FK).
* `retained_fraction` (number, 0–1).
* `source_citation` (string).

### `yield_factor`

* `process_code` (enum).
* `basis` (enum) — `raw→cooked | cooked→raw` (directional).
* `mass_change_fraction` (number) — e.g., −0.2 for 20% water loss.

---

# 2) Ingestion Contract (what a new source must deliver + what we guarantee)

## 2.1 What we expect from a new source

**A. Source metadata**

* Name, version, license, citation, `kind` classification.
* Release date and refresh cadence.

**B. Foods table**

* Stable `external_food_id`.
* Human `label`; `brand` if branded.
* `state` + `prep_method` if available (raw/cooked/fermented/etc.).
* Serving information (amount, unit), household measure (if branded).
* Density (if liquids) or a clear way to get 100 g values.
* EP flag if values are already on edible portion.

**C. Nutrient rows**

* One row per (food × nutrient) with: **nutrient identifier**, amount, unit, basis, derivation (analytical/label/etc.), optional method codes, sample n/SE or equivalent dispersion indicators.
* If the nutrient system is *not* INFOODS, provide a **nutrient dictionary** for mapping (IDs, names, units, definitions).

**D. Coverage statement**

* % of foods with: energy, protein, fat, carbohydrate, sodium, sugar, fiber.
* Known gaps (e.g., “vitamin D missing for branded”).

**E. Provenance & quality**

* For each nutrient row, whether it’s analytical, computed or label; any flags for outliers or imputation.

---

## 2.2 What we do during ingestion (deterministic pipeline)

1. **Register source** → `nutrition_source`.

2. **Nutrient mapping**

   * Map source nutrients to `nutrient_def` via `nutrient_alias_map`.
   * Add missing aliases with `confidence` < 1.0 only if unambiguous after review.
   * Refuse to ingest rows whose nutrient cannot be mapped.

3. **Unit & basis normalization eligibility**

   * Validate `unit` is UCUM; if not, add a controlled conversion or reject.
   * Mark rows convertible to `per_100g` using serving size, density, or EP flags.
   * Keep non-convertible rows but **exclude** them from rollups by default, noting `basis_unconvertible`.

4. **Food mapping**

   * Autolink `external_food` → graph nodes using your ontology:

     * TP (raw/primary) mappings use taxon + part cues.
     * TPT (prepared) mappings use transform hints in labels (e.g., “smoked”, “Greek”, “salted”, “pressed”, “aged”).
   * Keep `external_food_mapping.method` and `confidence`. Human accept high-impact ambiguous cases.

5. **QC**

   * Hard bounds per nutrient (e.g., sodium ≤ 100 g salt equivalent, protein ≤ 100 g/100 g, negative values forbidden unless defined as below-LOD sentinel which we normalize to 0 with a `flags.lod` note).
   * Cross-checks: if both `ENERC_KCAL` and macros present, verify within tolerance (±8%) to flag potential label rounding issues.
   * Deduplicate identical rows across overlapping sub-releases.

6. **Rollup**

   * Normalize eligible rows to canonical unit + `per_100g`.
   * Weight rows (tier → weight; optional recency decay for branded).
   * Filter outliers (MAD/IQR).
   * Aggregate (**weighted median** default).
   * Persist to `nutrition_profile_current` + `nutrition_profile_provenance`.

7. **Diagnostics**

   * Emit variance flags, basis-mix flags, and a `provenance_summary`.

---

## 2.3 Acceptance checks (must pass before profiles ship)

* **Mapping yield:** ≥ X% of external foods mapped to at least one node (policy: X depends on source type; 60–80% for commodity datasets; lower acceptable for branded).
* **Nutrient coverage:** core 6 nutrients present for ≥ Y% of mapped foods.
* **Energy reconciliation:** where both energy and macros exist, >90% rows within ±8%.
* **No unit/basis leaks:** 0 rows in `nutrition_profile_provenance.used=true` whose evidence couldn’t be normalized to per 100 g + canonical unit.
* **Outlier sanity:** share of rows excluded as outliers per nutrient ≤ Z% (tunable; typical 1–10%).
* **Provenance fidelity:** every profile has at least 1 row with `derivation ∈ {analytical, curated/survey}` unless marked `fallback_impute`.

---

# 3) Rollup policy (config object you can version)

### `nutrition_rollup_config` (conceptual)

* `tier_weights`: `{1:1.0, 2:0.7, 3:0.5, 4:0.3}`
* `recency_decay`: `{apply_to: ["branded"], lambda_per_year: 0.05}`
* `outlier_rule`: `{method: "mad", k: 3}` or `{method: "quantile", lower: 0.05, upper: 0.95}`
* `aggregator`: `{method: "weighted_median"}`
* `min_rows_per_profile`: `2` (fallback to `choose_best` if fewer)
* `confidence_threshold_for_mapping`: `0.7`
* `energy_reconciliation`: `{enabled: true, tolerance_pct: 8}`
* `imputation`: `{enabled: true, max_share_pct: 20}` (cap how much imputed content can drive a profile)
* `exclusions`: e.g., `{"nutrients": ["ALCOHOL"], "sources": []}`

Store a `config_version` string alongside profile rows for audit.

---

# 4) Guidance for mapping TP vs TPT

* **TP (taxon+part)**: map **raw or minimally processed** commodities (e.g., “Apple, raw, with skin”, “Beef, raw, ribeye”). Good for default “ingredient” nutrition.
* **TPT (prepared)**: map food entries whose labels encode transforms present in the node identity (e.g., “Bacon, cooked, pan-fried” → `cure + smoke + cook`; “Yogurt, Greek” → `ferment + strain`; “Olive oil, extra virgin” → `press` only).
* When a source has only raw forms but we need prepared: use **retention_factor** and **yield_factor** imputation with explicit low weight (derivation=`imputed`).

---

# 5) Glossary / invariants that keep the system sane

* **Canonical basis** is **per 100 g edible portion**. Liquids also normalize to per 100 g (we may *display* per 100 ml for UX, but profiles keep per 100 g for cross-category comparability).
* **INFOODS tagnames** anchor the nutrient vocabulary; all sources must map to these (or an extension we add deliberately).
* **Evidence immutability:** `external_*` rows are never edited in place; corrections are additional rows in a new `source_id` (new version).
* **Reproducibility:** Same evidence + same `nutrition_rollup_config` ⇒ same `nutrition_profile_current`.

---

# 6) Tiny worked example (one nutrient, one node)

* Node: `tpt:…:Greek yogurt (whole milk)`
* Evidence after mapping & normalization to per 100 g:

  * FDC Foundation: `PROCNT = 10.2 g` (tier 1)
  * CIQUAL: `PROCNT = 9.8 g` (tier 1)
  * Branded Label A: `PROCNT = 11.0 g` (tier 3)
  * Branded Label B: `PROCNT = 13.0 g` (tier 3) **outlier** (excluded)
* Weights: tier1=1.0; tier3=0.5
* Weighted median across {10.2 (w=1.0), 9.8 (1.0), 11.0 (0.5)} → **10.2 g/100 g**
* Stored as:

  * `nutrition_profile_current(tpt…, PROCNT) = 10.2 g`
  * `provenance`: three rows used (two tier1, one tier3); one excluded outlier.

---

# 7) What to do next (optional knobs)

* Pre-seed `nutrient_def` with the INFOODS core + commonly used vitamins/minerals/FA/amino acids.
* Decide your default `tier_weights` and `outlier_rule` once, version them (`config_version`), and commit them to the repo.
* Start with FDC (Foundation + SR Legacy + FNDDS) and one EU dataset (e.g., CIQUAL) to test cross-source reconciliation.
* Pick 10 representative nodes (5 TP, 5 TPT) as **golden profiles** to smoke-test the end-to-end flow and provenance UX.

---

