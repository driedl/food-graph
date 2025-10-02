
# North star

Treat everything the user searches or clicks as a **Food Node**:

* **T** = taxon (e.g., `tx:…:bos:taurus`)
* **TP** = taxon + part (e.g., cow + `part:milk`)
* **TPT** = curated derived food (taxon + part + transform sequence)

All three are peers in the graph and the search index. UI never parses strings; it sends/receives stable IDs (with the explicit `part:` prefix always preserved).

---

# Ontology: what we store

1. **Base**

   * Taxa, Parts, Transform families (tf) and their param shapes.
   * Applicability rules (which tf can apply to which `(taxon_prefix, part)`).

2. **Derived (curated)**

   * `derived_foods.jsonl` with:

     * `id` (e.g., `tpt:sus_scrofa_domesticus:cut:belly:bacon`)
     * `taxon_id`, `part_id`
     * `transforms[]` (ordered; identity tf first when relevant)
     * `name`, `synonyms[]`
     * optional: `tags[]` (`"dairy","fermented","korean"`), `notes`, `out_part_id?` (rarely needed)

3. **Name & synonym system**

   * Keep existing `name_overrides` and `taxon_part_synonyms` as sources.
   * Let derived foods carry their own high-priority synonyms (common market names).

4. **Identity rules**

   * Canonical **TPT identity hash** = `hash(taxon_id, part_id, normalized(transform_id + ordered identity params))`.
   * Distinguish **identity params** vs **process params** (small changes in cook temp shouldn’t mint new identities; different starter culture often should).

---

# Compilation (ETL): how it becomes a graph

1. **Validate**

   * Every TPT: transforms allowed for its `(taxon, part)`; parameters conform to tf schema.
2. **Normalize**

   * Fill tf defaults; strip non-identity params before hashing.
3. **Materialize nodes & edges**

   * Table (or MV) `food_nodes` with `id`, `doc_type` ∈ {T, TP, TPT}, `taxon_id`, `part_id`, `transform_path`, `name`, `synonyms`, `tags`, `popularity_score` (seeded; learned later).
   * Edges:

     * `T --has_part--> TP`
     * `TP --has_derived--> TPT`
     * Optional “is_variant_of” between TPTs that differ by minor params.
4. **Denormalized search payload**

   * `search_name` = name + synonyms + selected aliases.
   * token fields for `taxon_tokens`, `part_tokens` (keep `part:` prefix intact), `transform_tokens` (e.g., “smoked”, “cured”, “fermented”, “aged”).
   * lightweight locale fields for region/cuisine.

---

# Search structure: unify vs shard

## Recommendation: **Unified primary FTS + lightweight typed helpers**

* **Primary index**: one **`food_nodes_fts`** over all nodes (T, TP, TPT).

  * Pros: simpler global ranking, dedup, analytics, and mixed results (“bacon” + “pork belly” + “cow milk”).
  * Add a `doc_type` field for boosting.
* **Helper structures**:

  * **Prefix/autocomplete trie** per doc_type for snappy typeahead (optional).
  * **Facet store** for `taxon_family`, `part_kind`, `tags` to power filters.

### Why not separate shards only?

You can shard by T/TP/TPT, but then you’ll constantly merge/normalize scores across indexes and fight duplicates. Keeping one primary index avoids that; helpers keep UX fast.

---

# Search behavior & ranking

1. **Query parsing (server-side, not UI)**

   * Lexical FTS (BM25/FSDM) over `search_name`.
   * Synonym expansion (derived foods’ own synonyms first; then TP & taxon synonyms).
   * Optional semantic embeddings later (phase 2), blended with lexical.

2. **Intent heuristics**

   * Short commodity terms (e.g., “bacon”, “yogurt”) → boost **TPT**.
   * Part-like terms (“milk”, “brisket”) → boost **TP**.
   * Latin/common species cues → boost **T**.

3. **Signals for ranking**

   * **Exact name match** > synonym > alias > token overlap.
   * Popularity (click-throughs, saves), recency (curation freshness), region/cuisine tags relative to user locale.
   * Soft penalty for very long transform chains (favor familiar items first).

4. **Filters**

   * `doc_type` ∈ {T, TP, TPT}
   * `part_kind` (plant/animal/fungus/derived)
   * `tags` (fermented, smoked, cheese, etc.)
   * `taxon_family` (bovidae, salmonidae…), `cuisine`, `region`.

---

# APIs (clean, UI-friendly, no string parsing)

* **Search**

  * `GET /search?q=&docTypes[]=TPT&filters…`
  * Returns mixed results with `doc_type`, `id`, `name`, `highlights`, `badges` (e.g., “Derived”, “Part”, cuisine tags).

* **Lookup**

  * `GET /food-nodes/:id` → returns a normalized node payload:

    * Common fields: `id`, `doc_type`, `name`, `synonyms`, `taxon_id`, `part_id`, `tags`.
    * If **TP**: implied parts, applicable transforms (from rules).
    * If **TPT**: full `transform_path` with identity params, plus a “neighbor panel” (siblings under same TP, variants of same TPT).

* **Browse**

  * `GET /taxa/:taxonId/parts` → top TPs.
  * `GET /taxa/:taxonId/derived?partId=part:milk&tags=fermented` → curated TPTs for that branch.

* **Resolve/compose (power users & ETL checks)**

  * `POST /compile-tpt` with `{ taxon_id, part_id, transforms[] }` → validation + canonical identity hash + diff to nearest curated TPT (if any).

* **Suggest**

  * `GET /suggest?seedId=:id` → related nodes (e.g., from `TP milk` suggest “yogurt”, “kefir”, “cheddar”).

> Contract note: all inputs/outputs keep full IDs (`part:` prefix always present).

---

# UX patterns: where/how to surface TPT for impact

1. **Global search & typeahead**

   * Mixed results list with subtle **badges**: “Derived”, “Part”, “Taxon”.
   * If user types a canonical product name (“bacon”, “yogurt”, “kimchi”), the first hit is the **TPT** card with quick-view of the transform path (chips: *cure → smoke*).
   * Right rail shows filters: Part kind, Cuisine, “Only derived foods”.

2. **Entity pages**

   * **Taxon page (e.g., Cow)**

     * Sections: “Common parts” (TP grid), then “Popular derived foods” (TPT grid).
     * Let users pivot across taxa (e.g., “Goat yogurt” shown on Cow→Milk page as “Try with goat” chip).

   * **Part page (e.g., Milk)**

     * Group TPTs by style: Fresh → Fermented → Cheese → Butter/Fat → Concentrated/Dried.
     * Each card shows transform chips; clicking a chip filters to TPTs sharing that step.

   * **TPT page (e.g., Bacon)**

     * Hero: name, synonyms, badges (`pork belly`, `cured`, `smoked`).
     * Transform timeline (readable path with identity params only).
     * “Variants” rail (e.g., Pancetta, Guanciale) and “Swap taxon/part” (where meaningful) to encourage exploration.

3. **Builder mode (advanced)**

   * Start from a TP (e.g., `bos taurus + part:milk`) with an “Add transforms” tray.
   * As the user adds steps, **snap** to a known curated TPT if close enough (“Looks like Greek yogurt → open card”).
   * Never parse user text; the UI operates on IDs and transform selections.

4. **Contextual surfacing**

   * When a search lands on a **TP**, show a top banner: “Common derived foods from this part” (ranked TPT chips).
   * When a search lands on a **TPT**, show “Upstream” (its TP & Taxon) and “Downstream variants” (sibling TPTs).

5. **Empty/ambiguous queries**

   * If query matches both TP and TPT strongly (“salmon”), show a compact chooser: “Do you mean the fish (Taxon), fillet (Part) or smoked salmon (Derived)?” with one-tap disambiguation.

---

# Governance & analytics

* **Curation guardrails**: each TPT must include a short rationale & at least one synonym.
* **Linter** in CI: validate applicability, identity params, canonical ID format.
* **Telemetry**: search → click → node ID; promote high-CTR TPTs in ranking; demote low engagement.
* **A/B room**: test ranking knobs (doc_type boosts and transform familiarity penalty).

---

# Migration plan (sequenced, low-risk)

1. Add curated TPT list for a few high-impact domains (dairy, cured meats, fish, veg ferments, staple oils).
2. Implement **unified `food_nodes_fts`** and keep your current T/TP retrieval unchanged.
3. Ship the **search API** (mixed results) and **node lookup API**.
4. Enhance the **TP pages** with “Popular derived foods” and TPT chips.
5. Add **TPT detail pages** with transform timelines.
6. Instrument, tune boosts, then expand the curated TPT catalog.

---

# Why this works

* **Coherent identity**: T, TP, and TPT are first-class, making search & navigation consistent.
* **Curated surface area**: we avoid combinatorial explosion while mapping to real cultural foods.
* **Simple contracts**: stable IDs with explicit `part:` prefix; no UI parsing.
* **Scalable search**: one index to rank everything, with helpers for speed and facets.
* **Delightful UX**: users can find familiar foods (TPT) fast, but still discover the underlying biology (T + TP) and the transform logic behind it.

# Appendix

**T (Taxon)**
Biological identity only. Never carries process.

**P (Part)**
A **state-free substrate** you can plausibly “have” before further identity-bearing processing. Parts are:

1. **Anatomical/structural**: muscle, liver, seed, grain, fruit.
2. **Primary separations/exudates** (no composition change): milk, cream, whey, curd, expressed_juice, expressed_oil.
3. **Promoted derived parts**: cross-cultural, supply-chain commodities that function as substrates for **many** downstream transforms. (e.g., butter, flour, tofu — see promotion rules below)

**TPT (Derived food)**
A culturally recognized product whose identity **depends on a transform path** (parameters matter). Examples: bacon (cure+smoke), yogurt (ferment), kimchi (salt+ferment), extra-virgin olive oil (press w/ no refine), cheddar (curd+cook+press+age), Greek yogurt (ferment+strain), ghee (clarify_butter).

---

# The boundary rules (decision checklist)

## Promote to Part when the thing is:

1. **Produced mainly by fractionation/part-changing transforms** (separate, press, mill, churn, split, dehull)
2. **An upstream commodity** used broadly to make other things
3. **Parameter-stable** (small variations don't change its identity name)

## Keep as TPT when the thing is:

1. **Defined by identity-bearing transforms** (ferment, cure, smoke, age, stretch, refine, dry-as-identity)
2. **Sold/recognized as a finished product** with cultural identity
3. **Has identity parameters** (e.g., starter type, cure style, smoke mode) that change naming or family membership

## Examples (apply the rules):

* **Butter** → **Part** (promoted derived part). Source path (proto): separate(milk→cream) → churn; byproduct: buttermilk
* **Ghee / Brown butter** → **TPTs** derived from **part:butter** via `clarify_butter(stage=ghee|brown_butter)`
* **Plant milks (soy/oat/almond, etc.)** → **Parts** (promoted; upstream substrates for yogurts, tofu, ice creams)
* **Tofu** → **Part** (promoted; enables smoked/fermented/aged tofu TPTs)
* **EVOO / Virgin oils** → base **part:expressed_oil** remains a Part; **EVOO/virgin** are **TPTs** constrained by path (press-only, no refine)
* **Bacon/pancetta/prosciutto, yogurt/Greek/labneh, kimchi/sauerkraut/pickles** → **TPTs**

---

# Transform taxonomy (how transforms interact with parts)

## Transform Classes (to keep boundaries crisp)

* **Part-changing** (may yield/promote Parts): separate, press, mill, churn, split, dehull, polish
  *These justify parts (or promoted derived parts) on the output side*

* **Identity-bearing** (define TPT names/families): ferment, cure, smoke, age, stretch, refine_oil, salt (when intrinsic), dry (when intrinsic), evaporate (when intrinsic)

* **Finishing/non-identity** (metadata only): cook, blanch, soak, pasteurize, homogenize, standardize_fat, strain, press (when purely dewatering inside an existing identity)
  *These are usually covariates/attributes, not identity*

---

# Promotion policy (when a derived thing becomes a Part)

Mark candidate as **kind:"derived"** with a provenance path.

Promote when ≥2 of:

* **Substrate role:** used as the input for **≥3** distinct derived families in our catalog.
* **Supply chain:** commonly sold as an upstream commodity (retail/wholesale).
* **Cross-taxon/cuisine breadth:** appears across ≥2 cuisines or ≥2 taxa.
* **Stability:** process parameters don’t define its identity (i.e., “butter” is butter without specifying churn time).

If promoted, capture:

* `parent_id` (source part), and `proto_path` (minimal transform sequence producing it).
* Optional `byproducts` from the proto_path (e.g., churn yields buttermilk).

---

# Modeling patterns (with your examples)

## Dairy

* **Milk (part) → Cream (part, separation)**
* **Butter (promoted derived part)**: `proto_path=[tf:separate(milk→cream), tf:churn]`, `byproducts=[part:buttermilk(churned)]`.

  * **Ghee (TPT)** on butter: `[tf:clarify_butter(stage=ghee)]`.
  * **Brown butter (TPT)**: `[tf:clarify_butter(stage=brown_butter)]`.
* **Buttermilk**: split the concept:

  * **Churned buttermilk (promoted derived part)** via `proto_path=[tf:churn]`.
  * **Cultured buttermilk (TPT)**: milk + `[tf:ferment(culture_generic)]`.
* **Yogurt (TPT)**: milk + `[tf:ferment(yogurt_…)]`;
  **Greek yogurt (TPT)**: add `[tf:strain]`;
  **Labneh (TPT)**: ferment + strain (higher target solids).
* **Cheese family (TPTs)**: use **curd (part)** as the substrate:

  * Cheddar: `[tf:coagulate(rennet), tf:cook_curd, tf:press, tf:age]`
  * Mozzarella: `[tf:coagulate(… ), tf:stretch, (tf:salt)]`
  * Ricotta: **whey cheese** modeled from **whey (part)**: `[tf:coagulate(acid), tf:drain]`

## Meat & fish

* **Cuts (parts)**: belly, brisket, loin, fillet.
* **Bacon (TPT)**: belly + `[tf:cure(nitrite?), tf:smoke(hot/cold)]`
* **Pancetta (TPT)**: belly + `[tf:cure(dry, no smoke)]`
* **Prosciutto (TPT)**: leg/ham + `[tf:cure(long), tf:age]`
* **Smoked salmon (TPT)**: fillet + `[tf:cure?, tf:smoke(cold)]`

## Oils & grains

* **Expressed oil (part)** from seed/fruit via press;

  * **Refined oil (TPT)**: oil + `[tf:refine_oil(steps…)]`
  * **Virgin/EVOO (TPT)**: oil with **no `refine_oil`**; add press parameters if desired later.
* **Grain (part) → Flour (promoted derived part)** via `tf:mill(target=flour)`;

  * **Enriched flour (TPT)**: flour + `[tf:enrich(std_enriched)]`
  * **Semolina (promoted derived part)** via `tf:mill(target=semolina)`

## Fermented vegetables

* **Vegetable parts** (leaf, stem, fruit, etc.) stay as **parts**.
* **Kimchi / Sauerkraut / Pickles (TPTs)**: part + `[tf:salt/brine, tf:ferment]` (or can alone).
  Variants (e.g., “young kimchi”) are **TPT variants** (parameterized).

## Soy & plant proteins (use promotion rule)

* **Soy milk (promoted derived part)**: seed → soak + grind/press; (model as `part:soy_milk` or generic `part:plant_milk` if you want reuse).
* **Tofu**: **promote to part** if you plan many downstream identities (smoked, fried, fermented), else keep as **TPT**: soy milk + `[tf:coagulate, tf:press]`.

---

# Data modeling guidance (phase-1 scope)

## Minimal fields

**Taxon (T)**
* `id`, `display_name`, `rank`

**Part (P)**
* `id`, `name`, `kind: "anatomical"|"secreted"|"fraction"|"derived"`
* optional `parent_id`
* optional **`proto_path[]`** (for **promoted derived parts** only; transforms must be part-changing)
* optional **`byproducts[]`** (ids of Parts/TPTs)
* (optional) `cuisines[]`, `regions[]` (light metadata)

**Transform (TF)**
* `id`, `name`, `class: "part_changing"|"identity"|"finishing"`
* `params[]` (typed)
* `applies_to` matrix remains as you have it

**TPT (derived food)**
* `id`, `name`
* `taxon_id`, `part_id` (or promoted part id)
* `family_id` (see family archetypes below)
* **`path[]`** (ordered identity-bearing transforms with params)
* **`identity_params[]`** (subset of path params the name/family cares about)
* `synonyms[]`
* **`cuisines[]`, `regions[]`** (phase-1 on)
* **`dietary_compat[]`** (e.g., vegan/vegetarian/pescetarian/kosher?/halal? when determinable)
* **`safety_flags[]`** (simple booleans/labels derived from path: `pasteurized`, `nitrite_present`, `retorted`, `fermented`, `smoked`)

## Family archetypes (initial set)

(Drives grouping, facets, and consistent UI)

* **CULTURED_DAIRY** (yogurt, kefir, labneh): identity params → `starter`, `strain_level`
* **FRESH_CHEESE** (paneer, queso fresco, ricotta): `coagulate.agent`, `cook_curd?`
* **PASTA_FILATA** (mozzarella): `stretch.temp_C` bucket
* **PRESSED_COOKED_CHEESE** (cheddar/comté archetype): `age.time_d` bucket
* **DRY_CURED_MEAT** (prosciutto, pancetta): `cure.style`, `age.time_d` bucket, `nitrite`
* **SMOKED_MEAT_FISH** (hot/cold): `smoke.mode` (hot|cold)
* **BRINED_FERMENT_VEG** (kimchi, sauerkraut): `salt_pct` bucket, `time_h/d` bucket
* **PICKLED_VEG** (non-ferment acidified)
* **VIRGIN_OIL** (press only, no refine)
* **REFINED_OIL** (refine_oil steps)
* **FLOURS_MEALS** (promoted parts: flour, semolina, meal)
* **BUTTER_DERIVATIVES** (TPTs from butter: ghee, brown butter)

Each family defines which params are **identity** vs **variant** so names/facets stay stable.

## Identity discipline

* Only **identity-bearing params** contribute to the TPT identity hash (e.g., starter culture, presence of nitrite, hot vs cold smoke). Process minutiae (time/temp ranges) are covariates.

---

# Consistency rules & lint checks (phase-1)

## Invariants / lint (phase-1)

* No TPT without a valid `(taxon_id, part_id)` substrate
* Promoted Parts must have `proto_path` composed **only** of part-changing transforms
* All TFs used in `proto_path` or `path` must be allowed for the `(taxon, part)` by rules
* `identity_params ⊆ path.params`
* Family must declare ≥1 identity param
* Safety/diet flags are **derived** from `path`, not hand-edited

## What's in / out (explicit)

**In (phase-1)**
* Promoted Parts (butter, flours, plant milks, tofu) with `proto_path` + `byproducts`
* TPTs with `family_id`, `path[]`, `identity_params[]`
* `cuisines[]`, `regions[]`
* Derived **safety/diet flags** on TPTs

**Out (phase-2+)**
* Protected designations (PDO/PGI), deep safety/process semantics (F0, pH), localization/i18n, brand/compliance metadata

---

# UX implications (kept lean, driven by the trimmed ontology)

## Core pivots

1. **By Base** (Taxon→Part): start from salmon fillet / cow milk / soy milk / wheat flour
2. **By Family**: explore CULTURED_DAIRY, DRY_CURED_MEAT, VIRGIN_OIL, etc.
3. **By Product (TPT)**: direct lookup of "bacon", "Greek yogurt", "ghee"

## Card anatomy (Part vs TPT)

**Part card**
* Label + breadcrumb: `Taxon ▶ Part` (for promoted parts, show a tiny "made by: separate→churn" hint)
* "Common derived foods" rail → top TPTs from this substrate
* Light tags: `cuisines`, `regions` if present

**TPT card**
* Label + breadcrumb: `Taxon ▶ Part ▶ TPT`
* **Path chips** (identity steps only): e.g., `cure (dry, nitrite) → smoke (cold)`
* **Badges** from safety/diet flags: `fermented`, `smoked`, `nitrite-free`, `pasteurized`, `vegan`
* Metadata chips: `family_id`, `cuisines`, `regions`
* "How it's made" expand → humanized path from `path[]`
* "From this" & "Related" rails: upstream Part; sibling TPTs in same family

## Placement & impact

* **Base Part pages** (e.g., cow milk, soy milk, pork belly): surface **top family groupings** (CULTURED_DAIRY, CHEESE families; DRY_CURED_MEAT, SMOKED_MEAT_FISH)
* **Family pages**: shared facet blocks for identity params (e.g., smoke mode, starter, strain level)
* **Search result grouping**: cluster TPTs by **family**, then by **taxon/part**; Parts appear in a separate section with "popular derived foods" previews

