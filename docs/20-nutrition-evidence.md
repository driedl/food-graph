
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
