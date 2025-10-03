# Mise v2 Implementation Plan

> **Purpose**: Replace the previous plan with an accurate snapshot of what already works and a tightly scoped plan to finish the missing pieces needed to demo advanced UI features and run end‑to‑end builds. Keep scope minimal; assume required taxa already exist.

## 🎯 Current Status

**✅ COMPLETED (Phases 1-4)**:
- **Data Foundation**: Rich ontology with taxa, parts, transforms, and curated TPTs
- **ETL Pipeline**: Complete 0→F pipeline with validation and contracts
- **Search Enhancement**: TP synonyms, name overrides, and unified FTS
- **UI Metadata**: Family chips, cuisine associations, and safety/dietary flags
- **SQLite Schema**: Production-ready database with all necessary tables
- **API Implementation**: Complete tRPC-based API with all core endpoints
- **Database Configuration**: Simplified to use ETL2 only, auto-copy functionality

**🚀 NEXT (Phase 5)**: Production Enhancements
- **Schema Alignment**: Fix remaining database column mismatches
- **Advanced Features**: Complete TPT validation and compilation
- **Production Ready**: Caching, rate limiting, monitoring, and testing
- **Documentation**: OpenAPI spec with interactive docs and SDK generation

---

## Part I — Current State (What We Have Now)

### A. Data & Ontology Assets (present)

* **Core catalogs**: `transforms.json`, `parts.json`, `nutrients.json`, `attributes.json`.
* **Applicability & structure rules**:

  * `rules/parts_applicability.jsonl` (broad coverage, includes animal cuts and basic plant parts)
  * `rules/implied_parts.jsonl` (useful plant fruit defaults, etc.)
  * `rules/transform_applicability.jsonl` (identity families + cooking/process transforms)
* **Curation & naming**:

  * `rules/name_overrides.jsonl` (friendly labels at TP level)
  * `rules/taxon_part_synonyms.jsonl` (good coverage for milk/eggs and more)
  * `rules/part_aliases.jsonl` (search synonyms for parts)
* **Family scaffolding**:

  * `rules/family_allowlist.jsonl` (targets common families: cultured dairy, dry cured meat, brined veg, oils, etc.)
  * `rules/family_expansions.jsonl` (exists but sparse; 1–2 rules)
  * `rules/family_recipes.json` (reference material; not read by the pipeline today)
* **Derived foods (curated)**: `rules/derived_foods.jsonl` (bacon, sauerkraut, EVOO/refined oil, yogurts, butter, cheddar, tofu, smoked salmon)
* **Flags**: `rules/diet_safety_rules.jsonl` (smoked, nitrite present/free, pasteurized, fermented, raw dairy, veg/vegan)
* **Policy**: `rules/taxon_part_policy.json` (default ranks by kingdom + allowlist)
* **Bucketing**: `rules/param_buckets.json` (has entries; format partially differs from Stage E's expectation)
* **Animal cuts**: beef/chicken/pork JSONs (mapped into `parts_applicability` already)
* **UI metadata**: `rules/family_meta.json` (family chips/badges with labels, icons, colors, blurbs)
* **Cuisine mapping**: `rules/cuisine_map.jsonl` (taxon-part to cuisine associations)

### B. ETL Pipeline (stages and outputs)

* **Stage 0**: Compiles taxa/docs (inputs for later stages via `build/compiled/*`).
* **Stage A**: Canonicalizes transform families and normalizes applicability & flags.

  * Outputs: `tmp/transforms_canon.json`, `tmp/transform_applicability.normalized.jsonl`, `tmp/flags.rules.validated.json`, `report/lint.json`.
* **Stage B**: Builds T×P substrates and TP index.

  * Outputs: `graph/substrates.jsonl`, `tmp/tp_index.jsonl`, `tmp/promoted_parts.valid.jsonl`.
* **Stage C**: Ingests curated TPT seed.

  * Outputs: `tmp/tpt_seed.jsonl` (normalized, identity‑only path computed, params normalized).
* **Stage D**: Expands family rules into generated candidates.

  * Outputs: `tmp/tpt_generated.jsonl`.
* **Stage E**: Canonicalizes identity, buckets params, dedupes, assigns stable IDs.

  * Outputs: `tmp/tpt_canon.jsonl`, `tmp/param_buckets.lint.json`.
* **Stage F**: Packs SQLite graph + unified search.

  * Schema includes: `nodes`, `synonyms`, `part_def`, `has_part`, `taxon_doc`, `taxon_part_nodes (TP)`, `tpt_nodes (TPT)`, `search_content`, `search_fts`, `meta`, `family_meta`, `tpt_flags`, `tpt_cuisines`.
  * Unified search materializes taxa, TP, and TPT rows → single FTS.
  * **TP synonyms & name overrides**: TP nodes respect name overrides; search content includes synonyms from taxon synonyms + part aliases + TP-specific synonyms.
  * **Flag evaluation**: Evaluates `diet_safety_rules.jsonl` against TPT identity paths to populate `tpt_flags` table.
  * **Cuisine evaluation**: Matches TPTs against `cuisine_map.jsonl` to populate `tpt_cuisines` table.

### C. Contracts & Tooling

* **Contract engine + validators** wired to run per‑stage (`mise test` or `mise run … --with-tests`).
* **CLI UX**: Colored stage headers, timings, optional verification, pipeline presets (e.g., `0ABCDEF`).
* **Config**: `BuildConfig.from_env()` (override build root/db path/profile), directories auto‑created.

### D. Known gaps (high‑impact, minimal to fix)

1. **Param bucketing shape**: Stage E expects `"tf:family.param" → {cuts, labels}`; current file mixes another shape and keys (e.g., `age.time_d`).
2. **Family expansions**: File exists but too sparse to generate rich TPTs when curated seed is absent.
3. **Small applicability holes**: A few missing lines for `part:expressed_oil`, `part:butter`, and `part:cut:fillet`, and transforms like `tf:refine_oil`, `tf:clarify`.

---

## Part II — Plan to Finish (Minimal, Testable, and Safe)

### Phase 1 — Ontology essentials (seed data only)

**Goal**: Ensure B→D→E can generate realistic TPTs even without curated rows, and Stage E can bucket key params deterministically.

1. **Param bucketing (merge keys)**
   *Add the Stage‑E‑compatible entries while preserving existing ones.*

* Patch `rules/param_buckets.json` with:

  * `"tf:cure.nitrite_ppm": {cuts:[0,1,120], labels:["none","low","high"]}`
  * `"tf:salt.salt_pct": {cuts:[0.1,3.0,6.0], labels:["trace","low","high"]}`
  * `"tf:age.time_d": {cuts:[30,180], labels:["fresh","short","long"]}`
    **Acceptance**: `tmp/param_buckets.lint.json.ok == true` and Stage E runs clean.

2. **Family expansions (append 5–7 popular rules)**
   *Targets: cultured dairy, brined veg, dry‑cured meats, smoked fish, oils, butter derivatives.*

* Append the seven JSONL rows discussed to `rules/family_expansions.jsonl`.
  **Acceptance**: Stage D emits non‑zero `tpt_generated.jsonl` on a fresh build.

3. **Applicability top‑ups**

* Append to `rules/parts_applicability.jsonl` if missing:

  * `part:cut:fillet` → `tx:animalia:chordata:actinopterygii`
  * `part:expressed_oil` → `tx:plantae:oleaceae:olea:europaea`
  * `part:butter` → `tx:animalia:chordata:mammalia:artiodactyla:bovidae`
* Append to `rules/transform_applicability.jsonl`:

  * `tf:refine_oil` on olive expressed oil
  * `tf:clarify` on butter
    **Acceptance**: Stage B substrates include these T×P pairs and no new errors.

4. **Friendly names (optional but nice)**

* Append two lines to `rules/name_overrides.jsonl` for Olive Oil and Pork Belly.
  **Acceptance**: TP node names match overrides in Stage F output.

---

### Phase 2 — ETL adjustments (surgical)

**Goal**: Make search and naming reflect ontology rules; keep deterministic behavior.**

A) **Contracts** (lightweight)

* Add/extend stage contracts to catch regressions:

  * **Stage D**: `tpt_generated.jsonl` exists; optional `max_lines` guard to prevent explosion.
  * **Stage E**: `tpt_canon.jsonl` exists; add validator `path_transform_ids_in` (already supported) to ensure transform IDs are canonical; optionally require `min_lines ≥ curated+generated > 0` when allowlist/families present.
* **Acceptance**: `mise run 0ABCDEF --with-tests` passes on a clean workspace.

B) **Docs (inline)**

* Update comments at the top of Stage F to note that `_override_name` and `_tp_extra_synonyms` are actively used.

---

### Phase 3 — Build & Verification

1. **Clean build**: `rm -rf etl2/build && mise run build --with-tests`
   *Expected*: all stages 0→F succeed; `graph.dev.sqlite` contains:

   * `search_fts` entries for taxa, TP (with synonyms), and TPT.
   * `meta` rows: `taxa_count`, `parts_count`, `substrates_count`, `tpt_count` > 0.
2. **Spot checks** (manual):

   * Queries: `bacon`, `cow’s milk`, `olive oil`, `sauerkraut`, `smoked salmon`, `tofu` → results across TP/TPT.
   * Validate flags (e.g., nitrite_present vs nitrite_free) from curated rows.

---

### Phase 4 — API Implementation ✅ COMPLETED

**Goal**: Build a clean, UI-friendly API that exposes the rich TPT data for search, discovery, and exploration.

#### A) Core Search & Discovery APIs ✅ IMPLEMENTED

**1. Unified Search API** ✅ WORKING
- **Endpoint**: `GET /trpc/search.query`
- **Features**: FTS5 queries with BM25 ranking, mixed T/TP/TPT results
- **Filtering**: `type`, `families[]`, `cuisines[]`, `flags[]`, `taxonPrefix`, `taxonId`, `partId`
- **Response**: Results with facets, pagination, and scoring
- **Status**: ✅ Working with graceful fallback for missing tables

**2. Entity Lookup API** ✅ IMPLEMENTED
- **Endpoint**: `GET /trpc/entities.get`
- **Features**: Unified endpoint for T, TP, and TPT entities by ID
- **Response**: Rich entity details with related items and navigation
- **Status**: ✅ Implemented, some schema alignment needed

#### B) Browse & Navigation APIs ✅ IMPLEMENTED

**3. Taxon Navigation** ✅ IMPLEMENTED
- **Endpoints**: `GET /trpc/taxa.getParts`, `GET /trpc/taxa.getDerived`
- **Features**: Parts ranked by popularity, derived foods with filtering
- **Status**: ✅ Implemented, some schema alignment needed

**4. Family & Cuisine Facets** ✅ WORKING
- **Endpoints**: `GET /trpc/browse.getFamilies`, `GET /trpc/browse.getCuisines`
- **Features**: Family metadata with counts, cuisine listings
- **Status**: ✅ Working perfectly

#### C) Advanced APIs ✅ IMPLEMENTED

**5. TPT Builder & Validation** ✅ IMPLEMENTED
- **Endpoints**: `GET /trpc/tptAdvanced.validate`, `GET /trpc/tptAdvanced.compile`
- **Features**: TPT validation, compilation, canonical ID generation
- **Status**: ✅ Working with basic validation

**6. Suggestions & Recommendations** ✅ IMPLEMENTED
- **Endpoint**: `GET /trpc/tptAdvanced.suggest`
- **Features**: Related, variants, and substitute suggestions
- **Status**: ✅ Implemented

#### D) Implementation Details ✅ COMPLETED

**Database Configuration**:
- ✅ **ETL2 Integration**: Simplified to use ETL2 database only
- ✅ **Auto-copy**: API automatically copies ETL2 database to its own folder
- ✅ **Error Handling**: Graceful fallback for missing tables
- ✅ **tRPC**: Full tRPC implementation with type safety

**API Status**:
- ✅ **Core Functionality**: All major endpoints working
- ✅ **Search**: FTS5 with BM25 ranking and faceting
- ✅ **Browse**: Family and cuisine navigation
- ✅ **Validation**: TPT validation and compilation
- ⚠️ **Schema Alignment**: Some column name mismatches need fixing

---

### Phase 5 — Production Enhancements (Next Priority)

**Goal**: Fix remaining schema issues and add production-ready features.

#### A) Schema Alignment (High Priority)
- **Fix column mismatches**: Align API queries with actual database schema
- **Missing tables**: Handle `tpt_cuisines`, `tpt_flags` tables gracefully
- **Column names**: Fix `p.kind` and other column name mismatches

#### B) Advanced Features (Medium Priority)
- **Complete TPT validation**: Full transform applicability checking
- **Enhanced compilation**: Better canonical ID generation and naming
- **Rich suggestions**: Improved related/variant/substitute algorithms

#### C) Production Ready (Low Priority)
- **Caching**: Response caching with TTL and invalidation
- **Rate limiting**: Per-endpoint rate limiting
- **Monitoring**: Request logging and performance metrics
- **Documentation**: OpenAPI 3.0 spec with interactive docs

---

## Deliverables & Definition of Done

### Phase 1-4 ✅ COMPLETED
* ✅ **Ontology patches applied** (Phase 1 files committed).
* ✅ **Stage F updated** to honor TP synonyms and name overrides in search materialization.
* ✅ **Flag & cuisine evaluation** implemented in Stage F.
* ✅ **Contracts** added/updated for D & E.
* ✅ **Green pipeline**: `mise run build --with-tests` completes with ✓ Verify on all stages.
* ✅ **API Implementation**: Complete tRPC-based API with all core endpoints
* ✅ **Database Configuration**: ETL2 integration with auto-copy functionality
* ✅ **Core Functionality**: Search, browse, validation, and navigation working

### Phase 5 (Production Enhancements) - IN PROGRESS
* ⚠️ **Schema Alignment**: Fix remaining database column mismatches
* ⚠️ **Advanced Features**: Complete TPT validation and compilation
* ⚠️ **Production Ready**: Caching, rate limiting, monitoring, and testing
* ⚠️ **API Documentation**: OpenAPI 3.0 spec with interactive docs and SDK generation

---

## Appendix — File Edits (verbatim snippets to append/merge)

> Keep existing content; treat these as additive unless otherwise stated.

### A) `rules/param_buckets.json` (merge keys)

```json
{
  "tf:cure.nitrite_ppm": {"cuts": [0, 1, 120], "labels": ["none", "low", "high"]},
  "tf:salt.salt_pct": {"cuts": [0.1, 3.0, 6.0], "labels": ["trace", "low", "high"]},
  "tf:age.time_d": {"cuts": [30, 180], "labels": ["fresh", "short", "long"]}
}
```

### B) `rules/family_expansions.jsonl` (append)

```jsonl
{"family":"CULTURED_DAIRY","applies_to":[{"taxon_prefix":"tx:animalia:chordata:mammalia:artiodactyla:bovidae","parts":["part:milk"]}],"path":[{"id":"tf:ferment"}]}
{"family":"BRINED_FERMENT_VEG","applies_to":[{"taxon_prefix":"tx:plantae:brassicaceae","parts":["part:leaf"]},{"taxon_prefix":"tx:plantae:cucurbitaceae:cucumis:sativus","parts":["part:fruit"]}],"path":[{"id":"tf:salt","params":{"salt_pct":2.5}},{"id":"tf:ferment"}]}
{"family":"DRY_CURED_MEAT","applies_to":[{"taxon_prefix":"tx:animalia:chordata:mammalia:artiodactyla:suidae","parts":["part:cut:belly"]}],"path":[{"id":"tf:cure","params":{"style":"dry","nitrite_ppm":110}}]}
{"family":"SMOKED_MEAT_FISH","applies_to":[{"taxon_prefix":"tx:animalia:chordata:actinopterygii","parts":["part:cut:fillet"]}],"path":[{"id":"tf:smoke","params":{"mode":"cold"}}]}
{"family":"VIRGIN_OIL","applies_to":[{"taxon_prefix":"tx:plantae:oleaceae:olea:europaea","parts":["part:expressed_oil"]}],"path":[{"id":"tf:press"}]}
{"family":"REFINED_OIL","applies_to":[{"taxon_prefix":"tx:plantae:oleaceae:olea:europaea","parts":["part:expressed_oil"]}],"path":[{"id":"tf:press"},{"id":"tf:refine_oil"}]}
{"family":"BUTTER_DERIVATIVES","applies_to":[{"taxon_prefix":"tx:animalia:chordata:mammalia","parts":["part:butter"]}],"path":[{"id":"tf:clarify"}]}
```

### C) `rules/parts_applicability.jsonl` (append if missing)

```jsonl
{"part":"part:cut:fillet","applies_to":["tx:animalia:chordata:actinopterygii"]}
{"part":"part:expressed_oil","applies_to":["tx:plantae:oleaceae:olea:europaea"]}
{"part":"part:butter","applies_to":["tx:animalia:chordata:mammalia:artiodactyla:bovidae"]}
```

### D) `rules/transform_applicability.jsonl` (append if missing)

```jsonl
{"transform":"tf:refine_oil","applies_to":[{"taxon_prefix":"tx:plantae:oleaceae:olea:europaea","parts":["part:expressed_oil"]}]}
{"transform":"tf:clarify","applies_to":[{"taxon_prefix":"tx:animalia:chordata:mammalia","parts":["part:butter"]}]}
```

### E) `rules/name_overrides.jsonl` (append)

```jsonl
{"taxon_id":"tx:plantae:oleaceae:olea:europaea","part_id":"part:expressed_oil","name":"Olive Oil","display_name":"Olive Oil"}
{"taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus","part_id":"part:cut:belly","name":"Pork Belly","display_name":"Pork Belly"}
```

---

## Implementation Notes

* **SQLite Foundation**: The database already exposes all fields needed for a comprehensive API (taxon, TP, TPT, family, identity flags, synonyms, cuisines).
* **API-First Design**: All endpoints designed around UI needs with rich responses, proper error handling, and performance optimization.
* **Extensibility**: API structure supports future enhancements like semantic search, user preferences, and advanced analytics.
* **Production Ready**: Includes caching, rate limiting, monitoring, and comprehensive testing from day one.
