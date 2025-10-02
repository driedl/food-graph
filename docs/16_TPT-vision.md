
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

1. **Can you obtain it by simple separation without changing composition?**
   → **Part.** (milk ⇄ cream; fruit → expressed_juice; seeds → expressed_oil)

2. **Is it a widely traded intermediate used as a starting point for many distinct identities?**
   → **Promote to Part (kind: "derived").**
   Examples: butter (→ clarified/brown/ghee), flour (→ enriched/leavened/pasta), tofu (→ smoked/fried/fermented).
   Counter-examples (keep as TPT): yogurt, bacon, sauerkraut (used as ingredient, but not a major substrate for many identity-bearing families).

3. **Does its name encode the process/style (i.e., identity lives in the path)?**
   → **TPT.** (pancetta vs bacon; prosciutto; Greek yogurt; cold-smoked salmon)

4. **Would treating it as a Part explode combinatorics or blur categories?**
   → Keep as **TPT.** (e.g., “kimchi” as a part would make little sense)

5. **Do downstream transforms primarily tune **flavor/texture** without minting new product families?**
   → Keep upstream as **TPT**, model tweaks as **TPT variants** (same substrate & path family, different parameters).

---

# Transform taxonomy (how transforms interact with parts)

* **Part-changing transforms** (create new substrates): separate, press, churn, coagulate, split, dehull.
  *These justify parts (or promoted derived parts) on the output side.*

* **Identity-bearing state transforms** (mint product identity; usually TPT): ferment, cure, smoke, age, stretch, cook_curd, refine_oil, dry (when used to define a product, e.g., milk powder).

* **Non-identity/finishing transforms** (don’t usually mint new identities): cook (table prep), blanch, soak, pasteurize, homogenize, standardize_fat.
  *These are usually covariates/attributes, not identity.*

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

# Data modeling guidance (light changes)

**Parts**

* Add optional fields (non-breaking):

  * `parent_id`: lineage (e.g., butter ← cream ← milk)
  * `kind`: `"anatomical" | "secreted" | "fraction" | "derived"`
  * `proto_path`: minimal transforms to obtain this part (list of `{id, params?}`)
  * `byproducts`: list of `{part_id, notes}`

**Transforms**

* Add optional `yields_hint` for part-changing transforms (doc only, used by ETL validation).
  Example: `tf:churn` → yields `part:butter` (+ byproduct `part:buttermilk`) when substrate is `part:cream`.

**Derived foods (TPT)**

* Keep `out_part_id` optional for cases where the end state is best thought of as a named product **still grounded on a substrate** (usually not needed; butter/ghee handled by part + TPT above).

**Identity discipline**

* Only **identity-bearing params** contribute to the TPT identity hash (e.g., starter culture, presence of nitrite, hot vs cold smoke). Process minutiae (time/temp ranges) are covariates.

---

# Consistency rules & lint checks

* A **promoted derived part** must have a `proto_path` that consists only of **part-changing** steps (or separations).
* **TPT** must start from a **part** (including derived parts).
* If a TPT is extremely common as a substrate for ≥3 other TPT families, **consider promotion** (e.g., tofu).
* Avoid cyclic promotions (don’t promote “Greek yogurt” to part; it’s too style-defined).
* Keep **part:** prefix everywhere; UI never parses—always uses IDs.

