# Nutrition Graph — Contributor Handbook (for Humans & Agents)

This is the single source of truth for how to extend our food ontology and make it usable in the API. It explains IDs, ranks, parts, transforms, rules, and the composition model, plus step-by-step playbooks and checklists.

---

## 0) Core Concepts

- **Taxa (`tx:`)**: The biological tree (plants, animals, fungi…). IDs are colon-separated paths:
  `tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus`.
- **Parts (`part:`)**: Anatomical or product subcomponents usable across taxa (e.g., `part:milk`, `part:curd`, `part:cut:ribeye`). Parts form a hierarchy and can have synonyms.
- **Transforms (`tf:`)**: Canonical processing steps (e.g., `tf:coagulate`, `tf:ferment`, `tf:strain`). Each has a JSON schema for parameters and an `identity` flag.
  **Important:** Only **identity** transforms are allowed in canonical composition paths.
- **Rules**:
  - **Parts applicability** (`rules/parts_applicability.jsonl`): Which parts apply to which taxa (by prefix).
  - **Transform applicability** (`rules/transform_applicability.jsonl`): Which transforms apply to which (taxon, part) pairs.

- **Composition**: `foodstate.compose` builds a canonical `fs:/…` path from `(taxonId, partId, transforms[])`, sorting transforms by `ordering` and serializing params canonically.
  Non-identity transforms are rejected at compose time.
- **Docs**: Optional human summaries per taxon (compiled via `docs.jsonl`).

> **Preference rule:** When in doubt, move “attributes” into **parts or transforms**. Legacy “styles” should become `tf:*` or `part:*`, not ad-hoc attributes.

---

## 1) IDs, Ranks, Naming

### 1.1 Taxon IDs

- Format: `tx:<kingdom[:…]>`. Segments are **latin** when available (species/genus), camel-safe ASCII.
- Required fields in JSONL rows:
  `{"id","rank","display_name","latin_name","aliases":[],"parent":<id> (except root)}`
- **Ranks supported today** (code):
  `root | domain | kingdom | phylum | class | order | family | genus | species | cultivar | variety | breed | product | form`
- **Sub-species guidance**:
  - Plants: Prefer `variety` (var.) or `form` (f.) as we already support these; use `cultivar` for named cultivars.
  - Animals: Prefer `breed` for domesticated distinctions.
  - If strict subspecies (zoological/botanical) becomes necessary, we can add `subspecies` rank later; for now, map to `variety` (plants) or `breed` (animals) unless scientific subspecies is nutritionally/practically critical.

### 1.2 Slugs, Names, Aliases

- `slug` is auto-derived by compiler from the tail segment of `id` and lower-cased.
- `display_name` is the human-friendly string (e.g., “Chicken”).
- `aliases` are lower-cased synonyms matched in search; avoid duplicates and marketing fluff.

### 1.3 File Layout (source of truth)

- **Taxa**: `data/ontology/taxa/*.jsonl` (multiple files allowed; compiler merges).
- **Docs**: `data/ontology/docs.jsonl` (optional; compiled into DB).
- **Parts**: `data/ontology/parts.json`
- **Animal cuts**: `data/ontology/animal_cuts/*.json`
- **Transforms**: `data/ontology/transforms.json`
- **Rules**:
  `data/ontology/rules/parts_applicability.jsonl`
  `data/ontology/rules/transform_applicability.jsonl`
- **Smoke tests**: `data/ontology/smoke_tests/edible_paths.json`

---

## 2) Parts

### 2.1 What is a part?

- An anatomical or product subcomponent that can be “the thing you eat or process next.” Examples:
  - Cross-kingdom: `part:seed`, `part:oil` (derived), `part:flour`
  - Animal: `part:muscle`, `part:fat`, `part:organ:liver`, `part:cut:ribeye`
  - Dairy: `part:milk`, `part:cream`, `part:curd`, `part:whey`, `part:butter`, `part:buttermilk`

- Parts are **reusable** across taxa; applicability is controlled by rules.

### 2.2 Part hierarchy & synonyms

- Defined in `parts.json` with optional `parent_id`, `kind`, `notes`, and `aliases`.
- **Animal cuts** are maintained as trees in `animal_cuts/*.json`, each file listing `taxa` it applies to. Compiler ingests these into `part_def` and creates `has_part` pairs for all listed taxa.

### 2.3 Applying parts to taxa

Two ways:

1. **Built-in**: parts may include `"applies_to": ["tx:…prefix"]` in `parts.json` (rare; use sparingly).
2. **Rules**: `rules/parts_applicability.jsonl` lines like:

   ```json
   {
     "part": "part:milk",
     "applies_to": ["tx:animalia:chordata:mammalia:artiodactyla:bovidae"]
   }
   ```

   Optional:

   ```json
   {
     "part": "part:cut:ribeye",
     "applies_to": ["tx:animalia:chordata:mammalia:artiodactyla:bovidae"],
     "exclude": [
       "tx:animalia:chordata:mammalia:artiodactyla:bovidae:ovis:aries"
     ]
   }
   ```

---

## 3) Transforms

### 3.1 Definition

- Each transform in `transforms.json` has:
  - `id` (e.g., `tf:coagulate`)
  - `name`
  - `identity: true|false` (**Only identity transforms may appear in canonical paths**)
  - `params`: array of `{key, kind, enum?}` with kinds: `number | boolean | string | enum`
  - `order`: integer sort key (lower runs earlier)

**Canonicalization**:

- Composer sorts transforms by `order` and encodes params as `k=v` pairs sorted by key.
- Example chain segment: `tf:coagulate{agent=rennet,substrate=milk,temp_C=37,time_min=30}`

### 3.2 Applicability

- `rules/transform_applicability.jsonl` attaches transforms to (taxon_prefix × parts):

  ```json
  {
    "transform": "tf:coagulate",
    "applies_to": [{ "taxon_prefix": "tx:…:bovidae", "parts": ["part:curd"] }]
  }
  ```

- Use `exclude` to block subsets:

  ```json
  {
    "transform": "tf:coagulate",
    "applies_to": [{ "taxon_prefix": "tx:…:bovidae", "parts": ["part:curd"] }],
    "exclude": [{ "taxon_prefix": "tx:…:capra:hircus", "parts": ["part:curd"] }]
  }
  ```

### 3.3 Identity vs. covariates/facets

- **Identity transforms**: define the food (e.g., `ferment`, `coagulate`, `strain`, `press`, `age`, `smoke`, `evaporate`, `dry`, `clarify_butter`).
- **Non-identity transforms** (future): pasteurization, homogenization, fortification, packaging. These are **rejected by composer** and should be stored elsewhere when we add a covariates layer.

---

## 4) Composition Model

- Input: `{ taxonId, partId, transforms[] }`
- Validation:
  1. Taxon & part must exist; part must be applicable to the taxon lineage.
  2. Each transform must be defined, **identity=true**, and applicable to (lineage × part).
  3. Params validated against schema (type/enum).

- Output: canonical path:
  `fs:/<tx-tail>/<partId>/(tf…/tf…)`
  - `<tx-tail>` is the taxon id without the `tx:` prefix (with `:` turned into `/`).
  - Example:
    `fs:/animalia/chordata/mammalia/artiodactyla/bovidae/bos/taurus/part:curd/tf:coagulate{agent=rennet,substrate=milk,temp_C=37,time_min=30}/tf:age{time_d=30,temp_C=8,humidity_pct=85}`

---

## 5) Modeling Guidance

### 5.1 When to add a taxon vs. use transforms

- **Add/extend taxon** when the biological entity differs (species/genus/cultivar/breed) and that difference matters for names, sourcing, or nutrition.
- **Prefer transforms/parts** to capture processing “styles” (e.g., greek yogurt → `tf:strain`, not `style=greek`).
- **Avoid “product” leaf taxa** for things explainable as (part + transforms). Example: do **not** create `tx:…:cream_cheese`; use composition on `part:curd` from cream.

### 5.2 Derived foods (phaseable approach)

- **Phase 1 (now)**: single-ingredient derived foods modeled as `part + identity transforms`.
  Examples: yogurts, cheeses, ghee, ricotta, evaporated/condensed/powdered milk.
- **Phase 2 (later)**: multi-ingredient or reconstituted items (e.g., chocolate milk, processed cheese). This will need **formulations** (ingredient graph + transform chain). For now, skip or mark as “next phase.”

### 5.3 Subspecies & breeds

- If the market name hinges on subspecies/breed (e.g., water buffalo mozzarella), model with `species` + `breed` (if domesticated) or distinct `species` node if actually different species.
- Reserve `variety/cultivar` for plants where market names hinge on varietals (e.g., `‘Hass’` avocado, apple cultivars).

### 5.4 Deleting/merging suspicious taxa

- Remove entries that are actually **parts** or **transformed products** masquerading as taxa (e.g., “pumpkin seed” as a taxon — should be `part:seed` under Cucurbita spp. with `tf:dry`).
- Merge duplicates and eliminate ambiguous placeholders (“…seed source” aliases, redundant product nodes).
- If in doubt: prefer **leaner taxonomy** and richer **part/transform** modeling.

---

## 6) Worked Examples

### 6.1 Add **Goat milk cheese**

**Goal**: Enable raw, fresh, and aged goat cheeses without adding product leaf nodes.

1. **Taxa**
   - Ensure Bovidae branch contains goat:

     ```
     {"id":"tx:animalia:chordata:mammalia:artiodactyla:bovidae:capra","parent":"tx:animalia:chordata:mammalia:artiodactyla:bovidae","rank":"genus","display_name":"Goat (genus)","latin_name":"Capra","aliases":[]}
     {"id":"tx:animalia:chordata:mammalia:artiodactyla:bovidae:capra:hircus","parent":"tx:animalia:chordata:mammalia:artiodactyla:bovidae:capra","rank":"species","display_name":"Goat","latin_name":"Capra hircus","aliases":["goat"]}
     ```

2. **Parts**
   - If parts are already applied at family level (`bovidae`), goat inherits: `part:milk`, `part:curd`, `part:whey`, etc.
     If not, add a rule:

     ```json
     {
       "part": "part:milk",
       "applies_to": ["tx:animalia:chordata:mammalia:artiodactyla:bovidae"]
     }
     ```

3. **Transforms**
   - Dairy transforms already apply to `bovidae` in `transform_applicability.jsonl`.

4. **Smoke tests**
   - Fresh chèvre (lactic, strained):

     ```json
     {
       "name": "Chevre (goat, lactic, strained)",
       "taxonId": "tx:animalia:chordata:mammalia:artiodactyla:bovidae:capra:hircus",
       "partId": "part:curd",
       "transforms": [
         {
           "id": "tf:coagulate",
           "params": {
             "agent": "cultured_acid",
             "substrate": "milk",
             "temp_C": 22,
             "time_min": 720
           }
         },
         {
           "id": "tf:strain",
           "params": { "target_TS_pct": 28, "drain_time_min": 120 }
         }
       ]
     }
     ```

   - Aged goat cheese:

     ```json
     {
       "name": "Goat cheese (aged)",
       "taxonId": "tx:animalia:chordata:mammalia:artiodactyla:bovidae:capra:hircus",
       "partId": "part:curd",
       "transforms": [
         {
           "id": "tf:coagulate",
           "params": {
             "agent": "rennet",
             "substrate": "milk",
             "temp_C": 32,
             "time_min": 45
           }
         },
         {
           "id": "tf:salt",
           "params": { "method": "dry", "salt_pct": 2, "time_h": 2 }
         },
         {
           "id": "tf:age",
           "params": { "time_d": 30, "temp_C": 10, "humidity_pct": 90 }
         }
       ]
     }
     ```

### 6.2 Add **Bison steaks**

**Goal**: Support raw steaks via animal cut parts (cooking transforms are out of scope for Phase 1).

1. **Taxa**: Already present (`…:bison:bison`).
2. **Parts**: Ensure bovine cut map includes bison in `animal_cuts/*.json`:

   ```json
   {
     "taxa": [
       "tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus",
       "tx:animalia:chordata:mammalia:artiodactyla:bovidae:bison:bison" // add this
     ],
     "parts": [
       {
         "id": "part:cut:ribeye",
         "name": "Ribeye",
         "children": [
           /* … */
         ]
       }
     ]
   }
   ```

   Compiler will attach all listed parts to bison.

3. **Smoke test** (raw identity, no cook step yet):

   ```json
   {
     "name": "Bison ribeye (raw)",
     "taxonId": "tx:animalia:chordata:mammalia:artiodactyla:bovidae:bison:bison",
     "partId": "part:cut:ribeye",
     "transforms": []
   }
   ```

---

## 7) Quality Checklist (Before PR)

1. **Taxa**
   - [ ] Correct rank/parent path; latin names accurate.
   - [ ] No product/processing leakage into taxonomy.
   - [ ] Aliases are lower-cased, minimal, non-marketing.

2. **Parts**
   - [ ] New parts placed into `parts.json` with proper parent and synonyms.
   - [ ] Applicability rules added (or included via animal cut maps).
   - [ ] No taxon-specific part dupes; prefer reusable parts with rules.

3. **Transforms**
   - [ ] Defined in `transforms.json` with `identity: true` if used in paths.
   - [ ] Parameters have minimal schema; enums exhaustive and documented.
   - [ ] `order` values keep canonical sequence (e.g., coagulate → strain → press → age).

4. **Rules**
   - [ ] `parts_applicability.jsonl` covers your taxon prefixes.
   - [ ] `transform_applicability.jsonl` covers (taxon_prefix × parts).
   - [ ] Exclusions added where needed.

5. **Composition**
   - [ ] Add/extend `smoke_tests/edible_paths.json` with representative cases.
   - [ ] Run ETL pipeline: `pnpm etl:build` (includes smoke tests automatically).
   - [ ] Ensure composer rejects non-identity transforms (enforced code path is in place).

6. **Docs (optional but nice)**
   - [ ] Add/update `docs.jsonl` records for new nodes (clear summary, updated_at).

---

## 8) Common Pitfalls & How to Avoid

- **Modeling “styles” as attributes** → Use `tf:*` or `part:*` instead.
  E.g., “greek yogurt” → `tf:strain` over yogurt curd.
- **Creating product leaf taxa** that are just (part + transforms). Keep taxonomy biological.
- **Forgetting applicability rules** → transforms/parts won’t show up in API; tests will fail.
- **Transform duplicates** → keep IDs unique (lint transform IDs before commit).
- **Ambiguous seeds/nuts** as taxa → prefer `part:seed` under the botanical taxon + transforms.

---

## 9) API Pointers (for spot-checks)

- `taxonomy.getChildren({ id })` — navigate tree.
- `taxonomy.getPartsForTaxon({ id })` — verify inherited parts.
- `taxonomy.getTransformsFor({ taxonId, partId })` — verify available transforms and schemas.
- `foodstate.compose({ taxonId, partId, transforms })` — get canonical `fs:/` path (errors must be empty).
- `docs.getByTaxon({ taxonId })` — confirm human summary if present.

---

## 10) Ordering Hints (Dairy Reference)

Suggested `order` values (monotonic; adjust if needed):

- `tf:ferment` (30)
- `tf:coagulate` (40)
- `tf:cook_curd` (50)
- `tf:strain` (60)
- `tf:press` (65)
- `tf:stretch` (70)
- `tf:salt` (75)
- `tf:age` (80)
- `tf:smoke` (85)
- `tf:evaporate` (90)
- `tf:dry` (95)
- `tf:clarify_butter` (100)

---

## 11) What to Delete (Examples)

- Any taxon that’s actually a **part** (e.g., “pumpkin seed”) → move to `part:seed` under Cucurbita spp., keep transforms (e.g., `tf:dry`).
- Any taxon that’s actually a **transform outcome** (e.g., “cream cheese” as a taxon) → represent via `part:curd` + `tf:coagulate{substrate=cream,agent=cultured_acid}` + `tf:strain`.

---

## 12) Roadmap Notes

- **Covariates/facets storage** (pasteurization, homogenization, fortification) will be added as a separate layer; composer will continue to only encode identity.
- **Subspecies rank** can be added if we hit real-world blocking cases; until then, use existing `variety/breed` ranks.
- **Multi-ingredient derived foods** (formulations) are phase 2.

---

### TL;DR — How to add “X”

1. **Add/verify taxon** (biological node only).
2. **Ensure parts** exist & are applicable to your taxon (rules or cut maps).
3. **Ensure transforms** exist with schemas and `identity=true`; add applicability rules.
4. **Write smoke tests** that exercise the intended identity chain.
5. **Compile + smoke**; fix any errors.
6. (Optional) **Docs** entries for new taxa.

With this, adding **goat milk cheese**, **bison steaks**, or any similar item should be straightforward and consistent.
