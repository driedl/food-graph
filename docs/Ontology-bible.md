# 📖 The Ontology Bible (vision spec)

> This document describes **the intended end-state** (not necessarily what you have today). It’s the single source of truth for authors and implementers.

## 0) Purpose & mental model

We model foods via three building blocks:

* **T (Taxon)**: biological source (e.g., `tx:plantae:eudicots:oleales:oleaceae:olea:europaea`)
* **P (Part)**: anatomical or process-derived component (e.g., `part:fillet`, `part:butter`)
* **TPT (Transformed Product)**: a concrete product of a (T, P) undergoing transforms (e.g., “Cold-smoked salmon”)

Authoring new foods = choosing a T, choosing/creating the right P (product-anchored), then describing its **identity path** (sequence of `tf:*` transforms with identity-bearing params).

Everything downstream (search facets, families, cuisine hints, safety flags) is computed from those primitives.

---

## 1) IDs & casing

### 1.1) ID Format Specifications (Technical Reference)

#### Taxon IDs (`tx:*`)
* **Format**: `tx:[segment][:segment...]`
* **Segment Pattern**: `[a-z0-9_]+` (lowercase letters, digits, underscores only)
* **Minimum Segments**: 2 (e.g., `tx:life`, `tx:plantae`)
* **Maximum Segments**: No hard limit (practical limit ~10 for readability)
* **Full ID**: No trailing colon (e.g., `tx:plantae:eudicots:brassicales:brassicaceae:brassica:oleracea`)
* **Prefix**: Ends with colon for hierarchical queries (e.g., `tx:plantae:eudicots:brassicales:brassicaceae:`)
* **Examples**:
  - `tx:life` (root)
  - `tx:plantae:eudicots:brassicales:brassicaceae:brassica:oleracea:italica` (variety)
  - `tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus` (species)

#### Part IDs (`part:*`)
* **Format**: `part:[segment][:segment...]`
* **Segment Pattern**: `[a-z0-9_]+`
* **Hierarchical**: Use `part:parent:child` only for true component relationships
* **Simple**: Use `part:{specific}` with `category` field for most cases
* **Examples**:
  - `part:fruit` (simple)
  - `part:egg:white` (hierarchical - white is component of egg)
  - `part:muscle:ribeye` (hierarchical - ribeye is cut of muscle)

#### Transform IDs (`tf:*`)
* **Format**: `tf:[segment]`
* **Segment Pattern**: `[a-z0-9_]+`
* **No Hierarchy**: Transforms are flat namespace
* **One ID → one schema**: Each transform has single definition with stable params
* **Examples**: `tf:cook`, `tf:ferment`, `tf:clarify_butter`

#### TPT IDs (`tpt:*`)
* **Format**: `tpt:{taxon_id}:{part_id}:{family}:{identity_hash}`
* **Identity Hash**: First 12 characters of SHA1 of canonical identity
* **Family**: Product family ID or "unknown"
* **Examples**: `tpt:tx:plantae:eudicots:brassicales:brassicaceae:brassica:oleracea:part:fruit:unknown:abc123def456`

#### Attribute IDs (`attr:*`)
* **Format**: `attr:[segment]`
* **Segment Pattern**: `[a-z0-9_]+`
* **Examples**: `attr:salt_level`, `attr:ripeness_bucket`

### 1.2) Validation Rules

* **Contiguous Paths**: No skipping intermediate ranks in taxon hierarchy
* **Parent Existence**: Every node must have valid parent (except `tx:life`)
* **Uniqueness**: All IDs must be globally unique within their namespace
* **File Alignment**: Items in family files must start with that family's ID
* **Banned Names**: No product names masquerading as taxa (e.g., "Brown Sugar", "Powdered Sugar")
* **Segment Format**: All segments must match `[a-z0-9_]+` pattern
* **Hierarchy Acyclicity**: No circular references in parent-child relationships

### 1.3) Rank ladders (kingdom-specific)
We use kingdom-specific patterns to maximize stability and LLM predictability *without forcing uniform depth*.

**Animal (keep phylum):**  
`kingdom → phylum → class → order → family → genus → species → [breed]`

**Plant:**  
`kingdom → major_clade → order → family → genus → species → [cultivar] → [variety]`

**Fungus:**  
`kingdom → class → order → family → genus → species`

Rationale:
- Animal phylum (e.g., **Chordata**, **Arthropoda**, **Mollusca**) is stable and widely used in existing data.
- Plant "division" is de-emphasized in APG; we standardize on a small, stable clade enum at tier2.
- Fungal phylum adds little practical value for foods; class-level identities are sufficient and more stable across sources.

#### 1.3.1) Plants (major_clade)
Use the restricted enum for `major_clade`:

`eudicots | monocots | gymnosperms`

Do **not** use deeper APG subclades at tier2 (e.g., `rosids`, `asterids`, `superrosids`, `superasterids`, `magnoliids`).  
Do **not** use synonyms like `eudicotyledons`/`monocotyledons`; use `eudicots`/`monocots` exactly.

#### 1.3.2) Animals
Include **phylum** (e.g., `chordata`, `arthropoda`, `mollusca`) before class. Example:
`tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus`

#### 1.3.3) Fungi
Tier2 is **class** (e.g., `agaricomycetes`, `saccharomycetes`). Do **not** include division/phylum for fungi.

### 1.4) Kingdom-Specific Rank Terminologies

#### Plants (`tx:plantae`)
* **Allowed Ranks**: `kingdom`, `family`, `genus`, `species`, `variety`, `cultivar`, `form`
* **Special Rules**:
  - No `order` rank - families live directly under kingdom
  - `variety` for botanical varieties (e.g., `Brassica oleracea var. italica`)
  - `cultivar` for cultivated varieties (e.g., `Solanum lycopersicum 'Roma'`)
  - `form` for processing variants (e.g., rice forms)

#### Animals (`tx:animalia`)
* **Allowed Ranks**: `kingdom`, `phylum`, `class`, `order`, `suborder`, `infraorder`, `family`, `subfamily`, `tribe`, `subtribe`, `genus`, `species`
* **Special Rules**:
  - Full biological hierarchy supported
  - `breed` mentioned in documentation but not implemented as explicit rank
  - Focus on species-level identification

#### Fungi (`tx:fungi`)
* **Allowed Ranks**: `kingdom`, `genus`, `species`, `variety`, `form`
* **Special Rules**:
  - Simplified hierarchy
  - `variety` for fungal varieties
  - `form` for processing variants

### 1.4) Part System Details

* **Core Parts**: Biological/anatomical + primary process parts (e.g., milk, cream, muscle, fruit)
  * `id`: lower_snake_case
  * `kind`: `"plant" | "animal" | "fungus" | "derived"`
  * `category` (required): clarifies role and enables filtering (e.g., `organ`, `cut`, `egg`, `grain`, `fruit`, `dairy`, `oil`, `muscle`, `fat`, `bone`)
  * `parent_id`: explicit; hierarchy must be acyclic
* **Derived Parts**: Product parts (butter, yogurt, hard cheese, lard, ghee, oil:virgin/refined, fillet)
  * Same schema as core parts
  * MUST set `kind:"derived"` and `parent_id` pointing to core part
* **Names**: `display_name` Title Case; synonyms are plain strings (no qualifiers like `(salted)`)

### 1.5) Implementation Guidelines for 3rd Parties

#### ID Generation Algorithm
1. **Validate Segment Format**: Ensure each segment matches `[a-z0-9_]+`
2. **Check Parent Existence**: Verify parent ID exists in hierarchy
3. **Enforce Contiguity**: No skipping intermediate ranks
4. **Validate Kingdom Rules**: Apply kingdom-specific rank constraints
5. **Ensure Uniqueness**: Check against existing ID registry

#### File Organization
* **Taxa Files**: Group by family, use family ID as file prefix
* **Naming Convention**: `{Family}--{description}.jsonl`


---

## 2) Files (what they are, how to use them)

### Core definitions

* **`taxa/*.jsonl`**: taxon backbone (biological graph). Source of truth for `tx:*`.
* **`parts.core.json`**: biological/anatomical + primary process parts (e.g., milk, cream, muscle, fruit).

  * Required fields: `id`, `name`, `kind`
  * Optional: `category`, `parent_id`, `notes`
  * Must NOT contain `kind:"derived"`
* **`parts.derived.jsonl`**: product parts (butter, yogurt, hard cheese, lard, ghee, oil:virgin/refined, fillet, fruit:peel:*).

  * Same schema as core parts
  * MUST set `kind:"derived"` and `parent_id` pointing into the merged universe
* **`build/parts.registry.json`**: merged registry (generated by Stage 0/A)

  * Single authoritative parts table used by all later stages
* **`transforms.json`**: registry for unit operations (`tf:*`) with:

  * `id`, `name`, `identity:boolean`, `order:int`, and `params[]`
  * Each param: `{ key, kind, enum?, unit?, identity_param? }`
* **`families.json`**: product family definitions used for grouping/labeling.

  * Keys → `{ id, display_name, identity_transforms:[], identity_params?:[], naming, defaults, param_buckets }`
* **`family_allowlist.jsonl`**: applicability rules specifying which (taxon, part) combinations each family can be applied to.

  * Each line: `{ "family": "FAMILY_ID", "taxon_prefix": "tx:...", "parts": ["part:..."] }`
* **`param_buckets.json`** (optional): reusable numeric/enum bucket sets referenced by families.

### Rules & UX metadata

* **Family display names**: Defined in `families.json` with `display_name` field.

### Family System Architecture

The family system uses two complementary files:

* **`families.json`**: Contains family metadata (display names, transforms, naming rules, defaults, param buckets)
* **`family_allowlist.jsonl`**: Contains applicability rules (which taxon+part combinations each family can be applied to)

This separation allows:
- **Clean PR diffs**: Changes to applicability rules don't clutter family metadata
- **Focused maintenance**: Family definitions vs applicability rules are separate concerns  
- **Scalability**: Allowlist can grow without bloating the main families file
- **Precision control**: Prevents nonsensical TPTs (e.g., cultured dairy from fish muscle)
* **`rules/diet_safety_rules.jsonl`**: emitted flags when conditions match.

  * Grammar:

    * `{"when":{"has_transform":"tf:smoke"}, "emit":"smoked","flag_type":"safety"}`
    * `{"when":{"param":"tf:cure.nitrite_ppm","op":"gt","value":0}, ...}`
    * Supports `allOf`/`noneOf` as logical combinators.
* **`rules/cuisine_map.jsonl`**: attaches cuisine tags from `{taxon_prefix, parts}` (optionally transforms later).
* **`rules/name_overrides.jsonl`**: tidy display names for `(taxon_id, part_id)` pairs.
* **`rules/taxon_part_synonyms.jsonl`**: synonyms per `(taxon_id, part_id)`; no transform/marketing terms.

### Applicability

* **`parts_applicability.jsonl`**: which parts may apply to which taxa.

  * Encourage **prefix rules** with explicit `exclude` arrays.
* **`implied_parts.jsonl`** (optional): parts to auto-attach; must be subset of applicability.
* **Family expansion**: Families are expanded to (taxon, part) pairs based on `identity_transforms` in `families.json` and applicability rules in `family_allowlist.jsonl`.

### Product prototyping

* **`promoted_parts.jsonl`**: **recipes** for existing `part_id`s (no new IDs).

  * `proto_path` is a minimal transform chain that often produces that part.
  * This is **not** a replacement for authoring real TPTs; it seeds defaults.
  * No longer *defines* IDs; only carries recipes keyed by existing part IDs from the merged registry.

### Authoring T/PT/TPT

* **`taxon_part_nodes`** (generated): materialized `(T, P)` combos (TP). May be backfilled from TPTs.
* **`derived_foods.jsonl`** or `tpts.jsonl`: actual product instances (TPTs):

  * `{ id, taxon_id, part_id, family?, transforms[], name, synonyms[] }`
  * **`family`** (PREFERRED): Product family ID from `families.json` (e.g., `"CULTURED_DAIRY"`, `"DRY_CURED_MEAT"`)
  * **`transforms[]`**: Transform chain with identity-bearing parameters
  * **`identity[]`** is computed from `transforms[]` during ETL processing
  * **Auto-resolution**: Missing `family` field triggers automatic resolution based on transform path matching in Stage E

### Category Ontology

* **`categories.json`**: authoritative registry of all part categories with metadata.

  * Required fields: `id`, `name`, `description`, `kind`
  * `id`: category identifier used in parts (e.g., `"fruit"`, `"cut"`, `"dairy"`)
  * `name`: display name for UI (e.g., `"Fruit"`, `"Cut"`, `"Dairy"`)
  * `description`: human-readable description of the category
  * `kind`: biological kind this category applies to (`"plant"`, `"animal"`, `"fungus"`, `"derived"`)
  * **Single source of truth** for all category validation and UI display
  * **Self-validating** - validators read from this file, preventing data drift

---

## 3) Product-part anchoring (the "why" and "how")

**Why**: users think in products ("butter", "yogurt", "hard cheese"), not substrates ("cream", "milk"). Anchoring TPTs to product parts makes filtering, grouping, synonyms, and identity dedupe natural.

**How**:

* Put derived product parts in `parts.derived.jsonl` with `kind:"derived"` and correct `parent_id` → substrate.
* Build `part_ancestors` in Stage F (transitive closure).
* TPTs set `part_id` = product (e.g., `part:butter`), not the substrate.
* Queries like "is dairy?" become: `EXISTS (SELECT 1 FROM part_ancestors WHERE descendant_id=tpt.part_id AND ancestor_id='part:milk')`.

**Examples**:

```
part:butter (derived) → part:cream → part:milk
part:yogurt (derived) → part:fermented_milk → part:milk
part:cheese:hard (derived) → part:cheese → part:milk
```

---

## 4) Product-Part Anchoring Architecture

**Core parts** (`parts.core.json`): Biological/anatomical + primary process parts (e.g., milk, cream, muscle, fruit).
**Derived parts** (`parts.derived.jsonl`): Product parts (butter, yogurt, hard cheese, lard, ghee, oil:virgin/refined, fillet, fruit:peel:*).
**Registry merge**: Stage 0/A merges these into `build/parts.registry.json` (the single authoritative parts table used by all later stages).
**TPT anchoring**: Use product parts for derived foods (e.g., `part:butter`). Substrate queries use `part_ancestors` built from the merged registry.

### Files & Schemas

`parts.core.json` holds primary/anatomical parts. Must NOT contain `kind:"derived"`.
`parts.derived.jsonl` holds product parts. MUST use the same schema as core (id, name, kind, category, parent_id, notes). MUST set `kind:"derived"` and `parent_id` pointing into the merged universe (usually a core part).
The build step emits `build/parts.registry.json` which downstream stages consume as if it were a single `parts.json`.

### Guardrails (split registry)

1. **Uniqueness**: No duplicate `id` across core + derived.
2. **No orphan parents**: Every `parent_id` must resolve AFTER the union.
3. **No cycles** across the combined hierarchy.
4. **Kind vocabulary**: `plant|animal|fungus|derived|any` (schema-enforced).
5. **Biological ancestry for derived**: every `kind:"derived"` must trace to at least one biological ancestor (`plant|animal|fungus`) via `parent_id` links.
6. **Depth**: hierarchy depth ≤ 5 (configurable).
7. **Core purity**: `parts.core.json` must not contain `kind:"derived"`.

### Contributor workflow

- Add/modify anatomical parts in `parts.core.json`.
- Add/modify product parts in `parts.derived.jsonl` (JSONL; one object per line; same schema).
- Do **not** define IDs in `promoted_parts.jsonl` (recipes only).
- Run the build to generate `build/parts.registry.json`; review validation reports.

### Part Ancestry

`part_ancestors` is built from `part_def` loaded from `build/parts.registry.json`.

### Example: adding butter (split)

Add this line to `parts.derived.jsonl`:
`{"id":"part:butter","name":"butter","kind":"derived","category":"dairy","parent_id":"part:cream","notes":"Churned W/O emulsion from cream"}`
Confirm that `part:cream` exists in `parts.core.json` and that the merged registry validates.

### Promoted parts

`promoted_parts.jsonl` no longer *defines* IDs. It only carries **recipes** (e.g., `proto_path`, `byproducts`) keyed by existing part IDs from the merged registry.

---

## 5) Transforms & identity

* **Single source of truth** per `tf:id` (merged duplicates).
* **Stable `order`** provides deterministic identity reasoning.

  * Suggested anchors: `cure(60) → smoke(70) → cook(75) → age(80) → dry(90)`
* **Identity-bearing params** are explicitly marked (e.g., `tf:cure.style`, `tf:cure.nitrite_ppm`, `tf:smoke.mode`, `tf:clarify_butter.stage`).
* **Param units**: use canonical keys with units in key names where helpful (`temp_C`, `nitrite_ppm`, `salt_pct`).

---

## 6) Validation (ETL2, Stage F)

**SQLite schema adds**

* `part_ancestors(descendant_id, ancestor_id, depth)` (closure)
* Partial unique index on `(taxon_id, part_id, identity_hash) WHERE identity_hash IS NOT NULL`

**Soft/hard checks (split registry)**

* **Uniqueness**: No duplicate `id` across core + derived.
* **No orphan parents**: Every `parent_id` must resolve AFTER the union.
* **No cycles** across the combined hierarchy.
* **Kind vocabulary**: `plant|animal|fungus|derived|any` (schema-enforced).
* **Category required**: every part must have a `category` field for filtering and organization.
* **Biological ancestry for derived**: every `kind:"derived"` must trace to at least one biological ancestor (`plant|animal|fungus`) via `parent_id` links.
* **Depth**: hierarchy depth ≤ 5 (configurable).
* **Core purity**: `parts.core.json` must not contain `kind:"derived"`.
* TPT steps must reference known transforms, with known params.
* Enum values must be valid.

**Flag evaluation**

* The evaluator considers **all occurrences** of a transform when evaluating `when.param`.

---

## 7) Authoring checklist

### Adding a new product family

1. Add family to `families.json` with `id`, `display_name`, `identity_transforms`, `identity_params`, `naming`, `defaults`, and `param_buckets`.
2. Add applicability rules to `family_allowlist.jsonl` specifying which (taxon, part) combinations the family can be applied to.
3. (Optional) Add buckets in `param_buckets.json` and reference them.

### Adding/adjusting parts

1. **Anatomical parts**: Add to `parts.core.json` with `id`, `name`, `kind`, optional `category`, `parent_id`.
2. **Product parts**: Add to `parts.derived.jsonl` with same schema, MUST set `kind:"derived"` and `parent_id` pointing to core part.
3. Ensure ancestry makes sense and is acyclic across the merged registry.
4. If it's a product part, consider a `promoted_parts.jsonl` proto recipe (recipes only, no new IDs).

### Adding curated TPT records

1. Add to `derived_foods.jsonl` with `id`, `taxon_id`, `part_id`, `family?`, `transforms[]`, `name`, `synonyms[]`.
2. **`family` field is PREFERRED** - should reference a valid family ID from `families.json` for explicit classification.
3. **`transforms[]`** should contain only identity-bearing transforms with proper parameters.
4. **Auto-resolution**: Missing `family` field triggers automatic resolution based on transform path matching in Stage E.

### Adding transforms or params

1. Add to `transforms.json` with `id`, `name`, `identity`, `order`, `params[]`.
2. If renaming a param, update families, rules, exemplars to match.

### Authoring a TPT (“product instance”)

* Pick `taxon_id` (exact), `part_id` (product-part).
* Write `path[]` (full process) and `identity[]` (identity-bearing subset).
* Give a human `name` and optional `synonyms[]`.
* Run ETL + validators.

---

## 8) Worked examples (ready to paste)

**Greek yogurt (product anchored by substrate; OK because part is product of milk)**

```json
{
  "id":"tpt:tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus:part:milk:unknown:greek-yogurt",
  "taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus",
  "part_id":"part:milk",
  "family":"DAIRY_YOGURT",
  "path":[{"id":"tf:ferment","params":{"starter":"yogurt_thermo"}},{"id":"tf:strain","params":{"strain_level":6}}],
  "identity":[{"id":"tf:ferment","params":{}},{"id":"tf:strain","params":{}}],
  "name":"Greek Yogurt",
  "synonyms":["strained yogurt"]
}
```

**Ghee (anchored to product part: butter)**

```json
{
  "id":"tpt:tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus:part:butter:unknown:ghee",
  "taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus",
  "part_id":"part:butter",
  "family":"DAIRY_BUTTER",
  "path":[{"id":"tf:clarify_butter","params":{"stage":"ghee"}}],
  "identity":[{"id":"tf:clarify_butter","params":{}}],
  "name":"Ghee",
  "synonyms":["clarified butter"]
}
```

**Example: adding butter (split registry)**

Add this line to `parts.derived.jsonl`:
```json
{"id":"part:butter","name":"butter","kind":"derived","category":"dairy","parent_id":"part:cream","notes":"Churned W/O emulsion from cream"}
```

Confirm that `part:cream` exists in `parts.core.json` and that the merged registry validates.

**American bacon (identity via cure+smoke)**

```json
{
  "id":"tpt:tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus:part:belly:unknown:us-bacon",
  "taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus",
  "part_id":"part:belly",
  "family":"PORK_CURED_SMOKED",
  "path":[
    {"id":"tf:cure","params":{"style":"dry","nitrite_ppm":120}},
    {"id":"tf:smoke","params":{"mode":"hot","time_h":4,"temp_C":80}}
  ],
  "identity":[
    {"id":"tf:cure","params":{"style":"dry","nitrite_ppm":120}},
    {"id":"tf:smoke","params":{"mode":"hot"}}
  ],
  "name":"American Bacon",
  "synonyms":["streaky bacon (hot-smoked)"]
}
```

**Cold-smoked salmon (product anchored at cut)**

```json
{
  "id":"tpt:tx:animalia:chordata:actinopterygii:salmoniformes:salmo:salar:part:fillet:unknown:cold-smoked-salmon",
  "taxon_id":"tx:animalia:chordata:actinopterygii:salmoniformes:salmo:salar",
  "part_id":"part:fillet",
  "family":"FISH_CURED_SMOKED",
  "path":[
    {"id":"tf:cure","params":{"style":"dry","nitrite_ppm":0}},
    {"id":"tf:smoke","params":{"mode":"cold","temp_C":22,"time_h":12}}
  ],
  "identity":[
    {"id":"tf:cure","params":{"style":"dry","nitrite_ppm":0}},
    {"id":"tf:smoke","params":{"mode":"cold"}}
  ],
  "name":"Cold-smoked Salmon",
  "synonyms":["lox"]
}
```

**Salt cod (bacalhau)**

```json
{
  "id":"tpt:tx:animalia:chordata:actinopterygii:gadiformes:gadus:morrhua:part:fillet:unknown:bacalhau",
  "taxon_id":"tx:animalia:chordata:actinopterygii:gadiformes:gadus:morrhua",
  "part_id":"part:fillet",
  "family":"FISH_SALTED_DRY",
  "path":[
    {"id":"tf:salt","params":{"salt_pct":20,"method":"dry"}},
    {"id":"tf:dry","params":{}}
  ],
  "identity":[
    {"id":"tf:salt","params":{"salt_pct":20}},
    {"id":"tf:dry","params":{}}
  ],
  "name":"Salt Cod (Bacalhau)",
  "synonyms":["bacalhau","bacalao"]
}
```

---

## 9) Conventions & gotchas

* **Do not** encode transforms in synonyms (e.g., “smoked salmon”)—that belongs in TPT identity.
* **Eggs**: use `kind:"animal"` + `category:"egg"`; scope to birds/reptiles via applicability, not via `kind`.
* **Cuts**: are anatomical; use `kind:"animal"` with `category:"cut"` and `parent_id:"part:muscle"`.
* **Caviar**: is a **TPT** (salted roe), not a part. Keep `part:egg:fish:roe` as the part.

### Part Naming Convention

**Anatomical parts** (most common): Use `part:{specific}` with `category` field
- `part:shoulder` with `category: "cut"` (not `part:cut:shoulder`)
- `part:liver` with `category: "organ"` (not `part:organ:liver`)
- `part:fruit` with `category: "fruit"`
- `part:muscle` with `category: "muscle"`

**Hierarchical parts** (true parent-child relationships): Use `part:{parent}:{child}`
- `part:egg:white` (white is a component of egg)
- `part:egg:yolk` (yolk is a component of egg)
- `part:fat:leaf` (leaf fat is a type of fat)

**Why categories matter**: Enable filtering and searching by part type
- "Show all cuts": `WHERE category = "cut"`
- "Show all organs": `WHERE category = "organ"`
- "Show all dairy products": `WHERE category = "dairy"`

### Category Rules

**Category Ontology Requirements**:
- **All parts must have a valid category** from `categories.json`
- **Categories are immutable** - never hardcode category lists in validators
- **Single source of truth** - all category validation reads from `categories.json`
- **Rich metadata** - categories include `id`, `name`, `description`, `kind`

**Category Assignment Rules**:
- **Biological parts** use categories matching their biological function (`fruit`, `muscle`, `organ`)
- **Processed parts** use categories matching their product type (`dairy`, `oil`, `byproduct`)
- **Hierarchical parts** inherit category from parent when appropriate (`part:fat:leaf` → `category: "fat"`)
- **Consolidation** - group similar concepts (e.g., `pulp` and `serum` → `byproduct`)

**Category Validation**:
- **Schema compliance** - `part.schema.json` references `categories.json`
- **Runtime validation** - validators load categories dynamically
- **UI integration** - categories include display names and descriptions
- **Database integration** - categories are loaded into database for queries

