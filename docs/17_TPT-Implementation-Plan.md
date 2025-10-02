# 17 — TPT Implementation Plan

**Status**: Ready to Execute  
**Author**: System  
**Date**: 2025-01-27  
**Goal**: Implement the unified T/TP/TPT food node system as outlined in the TPT Vision document.

**Note**: This plan has been updated based on external review to align with current data structures and avoid schema drift. Key corrections include keeping promotion logic in rules files (reversible), fixing transform applicability, and ensuring proper identity parameter handling.

---

## Ground Rules & Context

This implementation operates under the following constraints and assumptions:

- **No Migration Concerns**: Database is rebuilt in ~3 seconds. We're in early development and can freely change schemas and wipe data. The database is read-only with only graph data from builds.
- **Build Artifacts**: `/dist` is for TypeScript compiled assets, not ETL build products. We'll use `/build` for ETL artifacts by design.
- **API Changes**: Breaking changes to API contracts are acceptable. We'll update the UI to match new interfaces.
- **Data Regeneration**: All metadata can be regenerated. Invalid data will be fixed during compilation rather than migrated.
- **POC Context**: This is a proof-of-concept with no deployed systems. No fancy migrations, backup plans, or rollback strategies needed.
- **Build Complexity**: ETL pipeline will build to JSONL files first (like current docs/taxa compilation), then to database.

---

## Executive Summary

This plan implements the **unified food node system** where T (Taxon), TP (Taxon+Part), and TPT (Taxon+Part+Transform) are first-class peers in search and navigation. The implementation follows the vision document's architecture while building on our existing TP foundation.

**Key Outcomes:**
- Unified `food_nodes_fts` search across all node types
- Curated TPT catalog with 25+ high-impact derived foods
- Enhanced part system with promotion rules and derived parts
- Complete API surface for food node operations
- Rich UX patterns for discovery and exploration

---

## Phase 1: Foundation & Ontology (Week 1)

### 1.1 Enhanced Parts System

**Goal**: Implement the part promotion system and derived parts as outlined in the vision.

**Key Insight**: Keep promotion logic in rules files (not in `parts.json`) to make promotions reversible and avoid schema churn. Parts remain "thin" with promotion metadata in `promoted_parts.jsonl`.

**Tasks:**

1. **Update Parts Schema** (`data/sql/schema/part.schema.json`)
   ```diff
   {
     "$id": "part.schema.json",
     "title": "Part",
     "type": "object",
     "required": ["id","name"],
     "properties": {
       "id": { "type": "string", "description": "Stable part ID, e.g., part:fruit, part:milk" },
       "name": { "type": "string" },
       "kind": { "type": "string", "description": "plant|animal|fungus|bird|derived|any" },
   +    "parent_id": { "type": "string", "description": "Optional: hierarchical parent part id" },
       "applies_to": { "type": "array", "items": { "type": "string" }, "description": "Optional list of taxon IDs this part explicitly applies to" },
       "notes": { "type": "string" }
     }
   }
   ```

2. **Add Missing Parts** (minimal additions to `parts.json`)
   - `part:plant_milk` (generic plant milk)
   - `part:tofu` (promoted derived part)
   - Note: `part:butter`, `part:buttermilk`, `part:curd`, `part:whey` already exist
   - **Data Regeneration**: All part metadata will be regenerated during compilation, fixing any inconsistencies

3. **Part Kind Classification** (keep existing biological buckets)
   - Keep `kind` as biological classification: `"plant"|"animal"|"fungus"|"bird"|"derived"|"any"`
   - Compute `part_category` at compile time: `"anatomical"|"secreted"|"fraction"|"derived"`
   - Place `part_category` in `search_docs.facets` for UI filtering
   - **Why**: Computing categories at compile time avoids schema migration while providing the categorization needed for UI filtering. This keeps the core schema stable while enabling rich search facets.

4. **Promotion Rules** (new file: `data/ontology/rules/promoted_parts.jsonl`)
   ```jsonl
   {"part_id":"part:plant_milk","proto_path":[{"id":"tf:mill"},{"id":"tf:strain"}],"byproducts":["part:okara"],"notes":"Aqueous extraction; okara is retained solids"}
   {"part_id":"part:tofu","proto_path":[{"id":"tf:coagulate","params":{"agent":"nigari"}},{"id":"tf:press"}],"byproducts":["part:tofu_serum"],"notes":"Pressed soy curd"}
   ```

5. **Add Missing Parts** (for tofu byproducts):
   - `part:okara` (plant fiber pulp from milling/straining)
   - `part:tofu_serum` (whey-like tofu serum)
   - **Parts Applicability**:
   ```jsonl
   {"part":"part:okara","applies_to":["tx:plantae:fabaceae:glycine:max:","tx:plantae:rosaceae:prunus:dulcis:","tx:plantae:poaceae:avena:sativa:"]}
   {"part":"part:tofu_serum","applies_to":["tx:plantae:fabaceae:glycine:max:"]}
   ```

6. **Update ETL Pipeline** (`etl/python/compile.py`)
   - Load promotion rules from `promoted_parts.jsonl`
   - Validate `proto_path` uses only part-changing transforms
   - Compute `part_category` facet during compilation

### 1.2 Transform System Enhancements

**Goal**: Add missing transforms and implement identity vs process parameter distinction.

**Key Insight**: Transform normalization is critical for stable identity hashing. Canonicalize parameter names and ensure `tf:refine_oil` is identity-bearing to distinguish virgin vs refined oils.

**Tasks:**

1. **Update Transform Schema** (`data/sql/schema/transform.schema.json`)
   ```diff
   {
     "$id": "transform.schema.json",
     "title": "Transform Family",
     "type": "object",
     "required": ["id","name","params","identity"],
     "properties": {
       "id": { "type": "string", "description": "tf:skim, tf:cook, tf:strain, tf:mill, tf:enrich" },
       "name": { "type": "string" },
       "identity": { "type": "boolean", "description": "True if transform is identity-bearing (affects FoodState identity)" },
   +    "order": { "type": "number", "description": "Relative ordering for path rendering and canonicalization" },
   +    "class": { "type": "string", "enum": ["identity","part_changing","finishing"], "description": "Optional semantic class; identity must align with identity=true" },
       "params": {
         "type": "array",
         "items": {
           "type": "object",
           "required": ["key","kind"],
           "properties": {
             "key": { "type": "string" },
             "kind": { "type": "string", "enum": ["number","string","enum","boolean"] },
             "unit": { "type": "string" },
             "enum": { "type": "array", "items": { "type": "string" } },
   +          "identity_param": { "type": "boolean", "description": "When true, param participates in TPT identity hashing" }
           }
         }
       },
       "notes": { "type": "string" }
     }
   }
   ```

2. **Transform Normalization** (critical for identity hashing):
   - **Make `tf:refine_oil` identity-bearing**: Set `"identity": true` (distinguishes virgin vs refined oils)
   - **Canonicalize smoke/cure parameters**:
     - `tf:smoke`: use `mode` (not `style`), mark as `identity_param: true`
     - `tf:cure`: use `style` and `nitrite_ppm` as identity params
   - **Handle `tf:skim` alias**: Treat as `tf:standardize_fat(fat_pct=0)` during canonicalization
   - **Identity Parameter Approach**: The proposed approach (identity_param flags) is better than the current system as it provides fine-grained control over which parameters contribute to identity hashing, enabling more precise TPT deduplication.
   - **Why**: Parameter name consistency is essential for stable identity hashing. Different parameter names for the same concept would create different hashes for identical transforms, breaking deduplication.

   **Implementation**: Apply JSON Merge Patch to `data/ontology/transforms.json`:
   ```json
   {
     "tf:smoke": {
       "id": "tf:smoke",
       "name": "Smoke",
       "identity": true,
       "class": "identity",
       "order": 70,
       "params": [
         { "key": "mode", "kind": "enum", "enum": ["cold", "hot"], "identity_param": true },
         { "key": "time_h", "kind": "number", "identity_param": false },
         { "key": "temp_C", "kind": "number", "identity_param": false }
       ],
       "notes": "Canonicalize to mode=cold|hot; temp/time are process params."
     },
     "tf:cure": {
       "id": "tf:cure",
       "name": "Cure",
       "identity": true,
       "class": "identity",
       "order": 60,
       "params": [
         { "key": "style", "kind": "enum", "enum": ["dry", "wet"], "identity_param": true },
         { "key": "nitrite_ppm", "kind": "number", "identity_param": true },
         { "key": "salt_pct", "kind": "number", "identity_param": false }
       ],
       "notes": "style + nitrite_ppm are identity-bearing."
     },
     "tf:refine_oil": {
       "id": "tf:refine_oil",
       "name": "Refine Oil",
       "identity": true,
       "class": "identity",
       "order": 90,
       "params": [
         { "key": "steps", "kind": "enum", "enum": ["degum", "neutralize", "bleach", "deodorize"], "identity_param": false }
       ],
       "notes": "Distinguishes virgin vs refined oils."
     },
     "tf:salt": {
       "id": "tf:salt",
       "name": "Salt",
       "identity": true,
       "class": "identity",
       "order": 55,
       "params": [
         { "key": "salt_pct", "kind": "number", "identity_param": true },
         { "key": "method", "kind": "enum", "enum": ["dry", "brine"], "identity_param": false }
       ],
       "notes": "salt_pct buckets drive BRINED_FERMENT_VEG naming."
     },
     "tf:clarify": {
       "id": "tf:clarify",
       "name": "Clarify",
       "identity": true,
       "class": "identity",
       "order": 95,
       "params": [],
       "notes": "Butter → Ghee/Brown butter archetypes live here."
     }
   }
   ```
   **Note**: If `transforms.json` is an array instead of a map, create `data/ontology/rules/transform_overrides.json` and have Stage A load/merge by `id`.

3. **Transform Class Classification** (update existing transforms with ordering):
   - **Part-changing** (order 10-35): `tf:separate` (10), `tf:dehull` (11), `tf:mill` (12), `tf:coagulate` (35), `tf:press` (30)
   - **Identity-bearing** (order 45-95): `tf:cook_curd` (45), `tf:stretch` (50), `tf:salt` (55), `tf:cure` (60), `tf:ferment` (65), `tf:smoke` (70), `tf:age` (80), `tf:evaporate` (85), `tf:dry` (86), `tf:refine_oil` (90), `tf:clarify` (95)
   - **Finishing/non-identity** (order 15-40): `tf:pasteurize` (15), `tf:homogenize` (16), `tf:standardize_fat` (17), `tf:strain` (40)
   - **Family Override for Identity**: `tf:strain` is finishing globally but treated as identity for CULTURED_DAIRY family
   - **Why**: Ordering is critical for deterministic identity hashing. Family overrides allow specific transforms to be identity-bearing only within certain families, enabling Greek/Labneh variants while keeping strain non-identity globally.

4. **Identity Parameter Marking**
   - Add `identity_param: true/false` to transform parameters
   - **Refactor `composeFoodState`**: Current function enforces identity-only transforms but needs update for TPT identity hashing
   - Update `foodstate.compose()` to only include identity params in hash
   - Distinguish identity params (starter culture, cure style, smoke mode) from process params (time, temperature ranges)

### 1.3 Transform Applicability Rules

**Goal**: Fix transform applicability rules to match actual substrate relationships and add missing veg ferment rules.

**Key Insight**: Transform applicability must reflect actual substrate relationships. `tf:coagulate` applies to milk/whey/cream (inputs), not curd (output). This is critical for path validation.

**Tasks:**

1. **Fix Dairy Transform Applicability** (`data/ontology/rules/transform_applicability.jsonl`):
   ```jsonl
   {"transform":"tf:coagulate","applies_to":[{"taxon_prefix":"tx:animalia:chordata:mammalia:artiodactyla:bovidae","parts":["part:milk","part:cream","part:whey"]}]}
   {"transform":"tf:strain","applies_to":[{"taxon_prefix":"tx:animalia:chordata:mammalia:artiodactyla:bovidae","parts":["part:curd","part:whey","part:milk"]}]}
   ```

2. **Add Vegetable Ferment Rules** (for sauerkraut/kimchi/pickles):
   ```jsonl
   {"transform":"tf:ferment","applies_to":[
     {"taxon_prefix":"tx:plantae:brassicaceae:brassica:oleracea:capitata","parts":["part:leaf"]},
     {"taxon_prefix":"tx:plantae:brassicaceae:brassica:rapa:subsp:pekinensis","parts":["part:leaf"]},
     {"taxon_prefix":"tx:plantae:cucurbitaceae:cucumis:sativus","parts":["part:fruit"]}
   ]}
   {"transform":"tf:salt","applies_to":[
     {"taxon_prefix":"tx:plantae:brassicaceae:brassica:oleracea:capitata","parts":["part:leaf"]},
     {"taxon_prefix":"tx:plantae:brassicaceae:brassica:rapa:subsp:pekinensis","parts":["part:leaf"]},
     {"taxon_prefix":"tx:plantae:cucurbitaceae:cucumis:sativus","parts":["part:fruit"]}
   ]}
   ```

3. **Add Plant Milk Processing Rules** (for tofu and plant milks):
   ```jsonl
   {"transform":"tf:mill","applies_to":[
     {"taxon_prefix":"tx:plantae:poaceae:avena:sativa","parts":["part:grain"]},
     {"taxon_prefix":"tx:plantae:poaceae:oryza:sativa","parts":["part:grain"]},
     {"taxon_prefix":"tx:plantae:rosaceae:prunus:dulcis","parts":["part:seed"]},
     {"taxon_prefix":"tx:plantae:fabaceae:glycine:max","parts":["part:seed"]}
   ]}
   {"transform":"tf:strain","applies_to":[
     {"taxon_prefix":"tx:plantae:poaceae:avena:sativa","parts":["part:grain"]},
     {"taxon_prefix":"tx:plantae:poaceae:oryza:sativa","parts":["part:grain"]},
     {"taxon_prefix":"tx:plantae:rosaceae:prunus:dulcis","parts":["part:seed"]},
     {"taxon_prefix":"tx:plantae:fabaceae:glycine:max","parts":["part:seed"]}
   ]}
   {"transform":"tf:coagulate","applies_to":[{"taxon_prefix":"tx:plantae:fabaceae:glycine:max","parts":["part:plant_milk"]}]}
   {"transform":"tf:press","applies_to":[{"taxon_prefix":"tx:plantae:fabaceae:glycine:max","parts":["part:curd"]}]}
   ```
   **Critical Fix**: `tf:press` applies to `part:curd` (output of coagulation), not `part:plant_milk` (input). This fixes the tofu compilation path where plant milk is coagulated to curd, then pressed to tofu.

### 1.4 Curated TPT Catalog

**Goal**: Implement the 25+ curated derived foods from external assessment with family archetypes.

**Key Insight**: Keep human-readable TPT IDs for better URLs and back-compatibility. Add `identity_hash` field for deduplication. Safety/diet flags must be conditional based on actual parameter values.

**Tasks:**

1. **Expand `data/ontology/rules/derived_foods.jsonl`** with curated foods:
   - Dairy: yogurt, greek yogurt, kefir, labneh, evaporated milk, sweetened condensed milk, milk powder, buttermilk, butter, ghee, mozzarella, cheddar, ricotta, feta
   - Meat: bacon, pancetta, pastrami, corned beef, smoked brisket
   - Fish: smoked salmon, gravlax, salt cod
   - Vegetables: sauerkraut, kimchi, fermented pickles
   - Oils: extra virgin olive oil, refined olive oil

2. **TPT ID Strategy**: Keep human-readable IDs + add identity hash
   - **Human-readable ID**: `tpt:bos_taurus:milk:yogurt` (for URLs and back-compatibility)
   - **Identity hash**: `3K2PH1Q9` (for deduplication and versioning)
   - **Final ID format**: `tpt:bos_taurus:milk:CULTURED_DAIRY:3K2PH1Q9` (includes family for grouping)
   - **Why**: Human-readable IDs provide better URLs and debugging, while identity hashes enable proper deduplication and versioning. This approach maintains back-compatibility while supporting advanced features.

3. **Enhanced TPT Schema** with conditional safety flags:
   ```json
   {
     "id": "tpt:bos_taurus:milk:yogurt",
     "identity_hash": "3K2PH1Q9",
     "taxon_id": "tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus",
     "part_id": "part:milk",
     "family_id": "CULTURED_DAIRY",
     "path": [
       {"id": "tf:ferment", "params": {"starter": "yogurt_thermo", "temp_C": 43, "time_h": 6}}
     ],
     "identity_params": {"starter": "yogurt_thermo"},
     "name": "Yogurt",
     "synonyms": ["Yoghurt", "Dahi"],
     "cuisines": ["western", "middle_eastern", "indian"],
     "regions": ["global"],
     "dietary_compat": ["vegetarian"],
     "safety_flags": ["fermented"]
   }
   ```

4. **Guarded Safety/Diet Flags System**:
   - **Schema-driven approach**: Use JSON Schema for rule validation and structured evaluation
   - **Conditional logic**: Support complex conditions with `allOf`/`anyOf`/`noneOf` operators
   - **Parameter-aware**: Check actual parameter values (e.g., `nitrite_ppm > 0`)
   - **Cross-reference validation**: Ensure all referenced transforms and parts exist
   - **Why**: This guarded approach prevents false positives and ensures accuracy. The schema-driven system provides better maintainability and validation than hardcoded logic.

   **Implementation**: Replace simple flag mapping with guarded rules system:
   - **Schema**: `data/sql/schema/flag_rule.schema.json` for rule validation
   - **Rules**: `data/ontology/rules/diet_safety_rules.jsonl` with conditional logic
   - **Validation**: `etl/python/lib/flags_validate.py` for cross-reference checks
   - **Evaluation**: `etl/python/lib/flags_eval.py` for runtime flag computation

5. **Family Archetypes Implementation**:
   - **CULTURED_DAIRY**: yogurt, kefir, labneh (identity params: starter, strain_level)
   - **FRESH_CHEESE**: paneer, queso fresco, ricotta (identity params: coagulate.agent, cook_curd?)
   - **PASTA_FILATA**: mozzarella (identity params: stretch.temp_C bucket)
   - **PRESSED_COOKED_CHEESE**: cheddar, comté (identity params: age.time_d bucket)
   - **DRY_CURED_MEAT**: prosciutto, pancetta (identity params: cure.style, age.time_d bucket, nitrite)
   - **SMOKED_MEAT_FISH**: bacon, smoked salmon (identity params: smoke.mode hot|cold)
   - **BRINED_FERMENT_VEG**: kimchi, sauerkraut (identity params: salt_pct bucket, time_h/d bucket)
   - **PICKLED_VEG**: non-ferment acidified pickles
   - **VIRGIN_OIL**: press only, no refine (EVOO, virgin oils)
   - **REFINED_OIL**: refine_oil steps
   - **FLOURS_MEALS**: promoted parts (flour, semolina, meal)
   - **BUTTER_DERIVATIVES**: ghee, brown butter (from part:butter)

### 1.5 Schema Updates & Rule Files

**Goal**: Implement the specific schema changes and rule files identified in the external review.

**Key Insight**: These changes are critical for the ETL compiler to work correctly. They fix transform applicability, enable proper identity hashing, and support the promotion system.

**Tasks:**

1. **Schema Updates** (ready-to-paste diffs):

   **`data/sql/schema/part.schema.json`**:
   ```diff
   {
     "$id": "part.schema.json",
     "title": "Part",
     "type": "object",
     "required": ["id","name"],
     "properties": {
       "id": { "type": "string", "description": "Stable part ID, e.g., part:fruit, part:milk" },
       "name": { "type": "string" },
       "kind": { "type": "string", "description": "plant|animal|fungus|bird|derived|any" },
   +    "parent_id": { "type": "string", "description": "Optional: hierarchical parent part id" },
       "applies_to": { "type": "array", "items": { "type": "string" }, "description": "Optional list of taxon IDs this part explicitly applies to" },
       "notes": { "type": "string" }
     }
   }
   ```

   **`data/sql/schema/transform.schema.json`**:
   ```diff
   {
     "$id": "transform.schema.json",
     "title": "Transform Family",
     "type": "object",
     "required": ["id","name","params","identity"],
     "properties": {
       "id": { "type": "string", "description": "tf:skim, tf:cook, tf:strain, tf:mill, tf:enrich" },
       "name": { "type": "string" },
       "identity": { "type": "boolean", "description": "True if transform is identity-bearing (affects FoodState identity)" },
   +    "order": { "type": "number", "description": "Relative ordering for path rendering and canonicalization" },
   +    "class": { "type": "string", "enum": ["identity","part_changing","finishing"], "description": "Optional semantic class; identity must align with identity=true" },
       "params": {
         "type": "array",
         "items": {
           "type": "object",
           "required": ["key","kind"],
           "properties": {
             "key": { "type": "string" },
             "kind": { "type": "string", "enum": ["number","string","enum","boolean"] },
             "unit": { "type": "string" },
             "enum": { "type": "array", "items": { "type": "string" } },
   +          "identity_param": { "type": "boolean", "description": "When true, param participates in TPT identity hashing" }
           }
         }
       },
       "notes": { "type": "string" }
     }
   }
   ```

2. **Transform Normalization** (in `data/ontology/transforms.json`):
   - Set `tf:refine_oil.identity = true`
   - Canonicalize `tf:smoke` to use `mode` parameter (not `style`)
   - Canonicalize `tf:cure` to use `style` and `nitrite_ppm` parameters
   - Treat `tf:skim` as alias for `tf:standardize_fat(fat_pct=0)`

3. **New Rule Files**:

   **`data/ontology/rules/promoted_parts.jsonl`** (new file):
   ```jsonl
   {"part_id":"part:plant_milk","proto_path":[{"id":"tf:mill"},{"id":"tf:strain"}],"byproducts":[],"notes":"Generic two-step aqueous extraction"}
   {"part_id":"part:tofu","proto_path":[{"id":"tf:coagulate","params":{"agent":"nigari"}},{"id":"tf:press"}],"byproducts":[],"notes":"Derived from soy plant milk"}
   ```

   **`data/ontology/rules/families.json`** (new file - complete consolidated families):
   ```json
   [
     {
       "id": "CULTURED_DAIRY",
       "identity_transforms": ["tf:ferment", "tf:strain?"],
       "identity_params": ["starter", "strain_level?"],
       "naming": {
         "template": "{baseName}",
         "variants": [
           { "when": { "strain_level": ">=7%" }, "name": "Greek Yogurt" },
           { "when": { "strain_level": ">=20%" }, "name": "Labneh" }
         ]
       },
       "defaults": { "cuisines": ["Global"] },
       "param_buckets": {
         "strain_level": [
           { "to": 4, "as": "light" },
           { "to": 10, "as": "greek" },
           { "to": 100, "as": "labneh" }
         ]
       }
     },
     {
       "id": "DRY_CURED_MEAT",
       "identity_transforms": ["tf:cure", "tf:age", "tf:smoke?"],
       "identity_params": ["cure.style", "cure.nitrite_ppm?", "smoke.mode?", "age.time_d"],
       "naming": { "template": "{substrate} {style}{smoke?}" },
       "param_buckets": {
         "age.time_d": [
           { "to": 30, "as": "fresh" },
           { "to": 180, "as": "short" },
           { "to": 9999, "as": "long" }
         ]
       }
     },
     {
       "id": "SMOKED_MEAT_FISH",
       "identity_transforms": ["tf:smoke"],
       "identity_params": ["smoke.mode"]
     },
     {
       "id": "BRINED_FERMENT_VEG",
       "identity_transforms": ["tf:salt", "tf:ferment"],
       "identity_params": ["salt_pct?", "time_d?"],
       "param_buckets": {
         "salt_pct": [
           { "to": 2.5, "as": "low" },
           { "to": 5.0, "as": "std" },
           { "to": 10.0, "as": "high" }
         ]
       }
     },
     {
       "id": "PICKLED_VEG",
       "identity_transforms": [],
       "identity_params": []
     },
     {
       "id": "PASTA_FILATA",
       "identity_transforms": ["tf:stretch"],
       "identity_params": ["stretch.temp_C?"],
       "param_buckets": {
         "stretch.temp_C": [
           { "to": 55, "as": "low" },
           { "to": 68, "as": "classic" },
           { "to": 90, "as": "high" }
         ]
       }
     },
     {
       "id": "FRESH_CHEESE",
       "identity_transforms": ["tf:coagulate", "tf:press?"],
       "identity_params": ["coagulate.agent", "cook_curd?"]
     },
     {
       "id": "PRESSED_COOKED_CHEESE",
       "identity_transforms": ["tf:cook_curd", "tf:press", "tf:age?"],
       "identity_params": ["age.time_d?"],
       "param_buckets": {
         "age.time_d": [
           { "to": 30, "as": "fresh" },
           { "to": 180, "as": "short" },
           { "to": 9999, "as": "long" }
         ]
       }
     },
     {
       "id": "VIRGIN_OIL",
       "identity_transforms": ["tf:press"],
       "identity_params": []
     },
     {
       "id": "REFINED_OIL",
       "identity_transforms": ["tf:press", "tf:refine_oil"],
       "identity_params": []
     },
     {
       "id": "FLOURS_MEALS",
       "identity_transforms": ["tf:mill"],
       "identity_params": []
     },
     {
       "id": "BUTTER_DERIVATIVES",
       "identity_transforms": ["tf:clarify"],
       "identity_params": []
     }
   ]
   ```
   **Why**: This complete families file prevents E003 errors by providing all family archetypes needed for TPT compilation. It includes the missing families for veg ferments, oils, and butter derivatives that were causing compilation failures.

   **`data/ontology/rules/family_allowlist.jsonl`** (new file):
   ```jsonl
   {"family":"CULTURED_DAIRY","taxon_prefix":"tx:animalia:chordata:mammalia:artiodactyla:bovidae","parts":["part:milk","part:cream"]}
   {"family":"DRY_CURED_MEAT","taxon_prefix":"tx:animalia:chordata:mammalia:artiodactyla:suidae","parts":["part:cut:belly"]}
   ```

   **`data/ontology/rules/param_buckets.json`** (new file):
   ```json
   {
     "age.time_d":[{"to":30,"as":"fresh"},{"to":180,"as":"short"},{"to":9999,"as":"long"}],
     "smoke.temp_C":[{"to":40,"as":"cold"},{"to":999,"as":"hot"}],
     "strain_level":[{"to":4,"as":"light"},{"to":10,"as":"greek"},{"to":100,"as":"labneh"}]
   }
   ```

   **`data/ontology/rules/diet_safety_map.json`** (new file):
   ```json
   {
     "dietary":{"part:milk":["vegetarian"],"part:butter":["vegetarian"],"tf:ferment":["fermented"],"tf:cure":["preserved"]},
     "safety":{"tf:ferment":["fermented"],"tf:smoke":["smoked"],"tf:cure":["nitrite_present"],"tf:pasteurize":["pasteurized"],"tf:can":["retorted"]}
   }
   ```

4. **Parts Applicability** (add to `data/ontology/rules/parts_applicability.jsonl`):
   ```jsonl
   {"part":"part:plant_milk","applies_to":["tx:plantae:fabaceae:glycine:max:","tx:plantae:rosaceae:prunus:dulcis:","tx:plantae:poaceae:avena:sativa:","tx:plantae:poaceae:oryza:sativa:"]}
   {"part":"part:tofu","applies_to":["tx:plantae:fabaceae:glycine:max:"],"exclude":[]}
   ```

---

## Phase 2: Database & ETL (Week 2)

### 2.1 ETL Build Structure Standardization

**Goal**: Implement proper build structure with ETL artifacts in `/build` and TypeScript assets in `/dist`.

**Key Insight**: By design, `/dist` is for TypeScript compiled assets, not ETL build products. ETL artifacts belong in `/build` to maintain clear separation and avoid confusion.

**Tasks:**

1. **Implement Build Structure**:
   - Create `etl/build/` for ETL build artifacts
   - Keep `etl/dist/` for TypeScript compiled assets only
   - Update environment variables to point to new build location
   - Update `@nutrition/config` paths for new structure

2. **Environment Variable Updates**:
   ```typescript
   // @nutrition/config/src/paths.ts
   export const ETL_BUILD_PATH = process.env.ETL_BUILD_PATH || 'etl/build'
   export const TPT_META_PATH = `${ETL_BUILD_PATH}/out/tpt_meta.jsonl`
   export const SEARCH_DOCS_PATH = `${ETL_BUILD_PATH}/out/search_docs.jsonl`
   export const NAVIGATION_PATH = `${ETL_BUILD_PATH}/out/navigation.json`
   export const FAMILIES_CATALOG_PATH = `${ETL_BUILD_PATH}/out/families_catalog.json`
   export const GRAPH_EDGES_PATH = `${ETL_BUILD_PATH}/graph/edges.jsonl`
   export const GRAPH_SUBSTRATES_PATH = `${ETL_BUILD_PATH}/graph/substrates.jsonl`
   ```

3. **Database Path Updates**:
   ```typescript
   // @nutrition/config/src/paths.ts
   export const DB_PATH = process.env.DB_PATH || 'etl/build/database/graph.dev.sqlite'
   ```

4. **New ETL Build Structure**:
   ```
   etl/
   ├── build/                    # ETL build artifacts
   │   ├── out/                  # Final deliverables
   │   │   ├── tpt_meta.jsonl    # Primary TPT cards
   │   │   ├── search_docs.jsonl # Search corpus
   │   │   ├── navigation.json   # Navigation data
   │   │   └── families_catalog.json
   │   ├── graph/                # Graph edges
   │   │   ├── substrates.jsonl
   │   │   └── edges.jsonl
   │   ├── tmp/                  # Intermediate files
   │   │   ├── transforms_canon.json
   │   │   ├── tpt_seed.jsonl
   │   │   ├── tpt_generated.jsonl
   │   │   ├── tpt_canon.jsonl
   │   │   └── tpt_named.jsonl
   │   └── report/               # Compilation reports
   │       └── lint.json
   ├── dist/                     # TypeScript compiled assets only
   └── data/ontology/rules/      # New rule files
   ```
   **Build Complexity**: This follows the existing pattern of building to JSONL files first (like current docs/taxa compilation), then to database. The 11-stage pipeline provides comprehensive validation and intermediate artifacts for debugging.

3. **New Rule Files** (add to `data/ontology/rules/`):

   **`promoted_parts.jsonl`** - Declares promoted derived parts + proto_path:
   ```jsonl
   {"part_id":"part:butter","proto_path":[{"id":"tf:separate","params":{"method":"centrifuge"}},{"id":"tf:churn"}],"byproducts":["part:buttermilk"]}
   {"part_id":"part:flour","proto_path":[{"id":"tf:mill","params":{"target":"flour"}}],"byproducts":[]}
   {"part_id":"part:tofu","proto_path":[{"id":"tf:coagulate","params":{"agent":"nigari"}},{"id":"tf:press"}],"byproducts":["part:tofu_serum"]}
   ```
   **Part Promotion**: All part promotion logic will be regenerated during compilation, ensuring consistency and fixing any existing metadata issues.


   **`family_allowlist.jsonl`** - Pragmatic allowlist for family × (taxon, part):
   ```jsonl
   {"family":"CULTURED_DAIRY","taxon_prefix":"tx:animalia:chordata:mammalia:artiodactyla:bovidae","parts":["part:milk","part:cream"]}
   {"family":"DRY_CURED_MEAT","taxon_prefix":"tx:animalia:chordata:mammalia:artiodactyla:suidae","parts":["part:cut:belly","part:cut:leg"]}
   {"family":"SMOKED_MEAT_FISH","taxon_prefix":"tx:animalia:chordata:actinopterygii","parts":["part:cut:fillet"]}
   {"family":"SMOKED_MEAT_FISH","taxon_prefix":"tx:animalia:chordata:mammalia","parts":["part:cut:belly","part:cut:shoulder"]}
   {"family":"BRINED_FERMENT_VEG","taxon_prefix":"tx:plantae:brassicaceae","parts":["part:leaf"]}
   {"family":"BRINED_FERMENT_VEG","taxon_prefix":"tx:plantae:cucurbitaceae:cucumis:sativus","parts":["part:fruit"]}
   {"family":"VIRGIN_OIL","taxon_prefix":"tx:plantae:oleaceae:olea:europaea","parts":["part:expressed_oil","part:fruit"]}
   {"family":"REFINED_OIL","taxon_prefix":"tx:plantae:oleaceae:olea:europaea","parts":["part:expressed_oil"]}
   {"family":"BUTTER_DERIVATIVES","taxon_prefix":"tx:animalia:chordata:mammalia","parts":["part:butter"]}
   {"family":"FLOURS_MEALS","taxon_prefix":"tx:plantae:poaceae:triticum","parts":["part:grain"]}
   {"family":"FLOURS_MEALS","taxon_prefix":"tx:plantae:poaceae:oryza:sativa","parts":["part:grain"]}
   {"family":"PASTA_FILATA","taxon_prefix":"tx:animalia:chordata:mammalia","parts":["part:curd"]}
   {"family":"FRESH_CHEESE","taxon_prefix":"tx:animalia:chordata:mammalia","parts":["part:milk","part:curd"]}
   {"family":"PRESSED_COOKED_CHEESE","taxon_prefix":"tx:animalia:chordata:mammalia","parts":["part:curd"]}
   ```

   **`param_buckets.json`** - Cross-family numerical bucketing:
   ```json
   {
     "age.time_d":[{"to":30,"as":"fresh"},{"to":180,"as":"short"},{"to":9999,"as":"long"}],
     "smoke.temp_C":[{"to":40,"as":"cold"},{"to":999,"as":"hot"}],
     "strain_level":[{"to":4,"as":"light"},{"to":10,"as":"greek"},{"to":100,"as":"labneh"}]
   }
   ```

   **`data/sql/schema/flag_rule.schema.json`** - JSON Schema for guarded flag rules:
   ```json
   {
     "$id": "flag_rule.schema.json",
     "title": "Guarded Flag Rule",
     "type": "object",
     "required": ["flag_type", "emit", "when"],
     "additionalProperties": false,
     "properties": {
       "id": { "type": "string", "description": "Optional stable id for diffs" },
       "flag_type": { "type": "string", "enum": ["safety", "dietary"] },
       "emit": { "type": "string", "description": "Flag token to emit (e.g., smoked, pasteurized, nitrite_present, vegetarian)" },
       "when": {
         "type": "object",
         "minProperties": 1,
         "additionalProperties": false,
         "properties": {
           "allOf": { "type": "array", "items": { "$ref": "#/$defs/cond" } },
           "anyOf": { "type": "array", "items": { "$ref": "#/$defs/cond" } },
           "noneOf": { "type": "array", "items": { "$ref": "#/$defs/cond" } }
         }
       },
       "notes": { "type": "string" }
     },
     "$defs": {
       "cond": {
         "oneOf": [
           { "$ref": "#/$defs/has_transform" },
           { "$ref": "#/$defs/has_part" },
           { "$ref": "#/$defs/param_cmp" }
         ]
       },
       "has_transform": {
         "type": "object",
         "additionalProperties": false,
         "required": ["has_transform"],
         "properties": {
           "has_transform": { "type": "string", "pattern": "^tf:[a-z0-9_]+$" }
         }
       },
       "has_part": {
         "type": "object",
         "additionalProperties": false,
         "required": ["has_part"],
         "properties": {
           "has_part": { "type": "string", "pattern": "^part:[a-z0-9_:]+$" }
         }
       },
       "param_cmp": {
         "type": "object",
         "additionalProperties": false,
         "required": ["param", "op"],
         "properties": {
           "param": {
             "type": "string",
             "description": "Param path like tf:cure.nitrite_ppm or tf:smoke.mode",
             "pattern": "^tf:[a-z0-9_]+(?:\\.[a-z0-9_]+)+$"
           },
           "op": {
             "type": "string",
             "enum": ["exists", "eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in"]
           },
           "value": {}
         },
         "allOf": [
           {
             "if": { "properties": { "op": { "const": "exists" } } },
             "then": { "not": { "required": ["value"] } }
           },
           {
             "if": { "properties": { "op": { "enum": ["in", "not_in"] } } },
             "then": { "properties": { "value": { "type": "array" } }, "required": ["value"] }
           }
         ]
       }
     }
   }
   ```

   **`data/ontology/rules/diet_safety_rules.jsonl`** - Guarded flag rules (replaces `diet_safety_map.json`):
   ```jsonl
   {"flag_type":"safety","emit":"smoked","when":{"allOf":[{"has_transform":"tf:smoke"}]}}
   {"flag_type":"safety","emit":"nitrite_present","when":{"allOf":[{"has_transform":"tf:cure"},{"param":"tf:cure.nitrite_ppm","op":"gt","value":0}]}}
   {"flag_type":"safety","emit":"nitrite_free","when":{"allOf":[{"has_transform":"tf:cure"},{"param":"tf:cure.nitrite_ppm","op":"eq","value":0}]}}
   {"flag_type":"safety","emit":"pasteurized","when":{"allOf":[{"has_transform":"tf:pasteurize"}]}}
   {"flag_type":"safety","emit":"fermented","when":{"allOf":[{"has_transform":"tf:ferment"}]}}
   {"flag_type":"safety","emit":"raw_dairy","when":{"allOf":[{"has_part":"part:milk"}],"noneOf":[{"has_transform":"tf:pasteurize"}]}}
   {"flag_type":"dietary","emit":"vegetarian","when":{"allOf":[{"has_part":"part:milk"}]}}
   {"flag_type":"dietary","emit":"vegan","when":{"allOf":[{"has_part":"part:plant_milk"}],"noneOf":[{"has_part":"part:milk"},{"has_part":"part:egg"}]}}
   ```

### 2.2 Comprehensive ETL Compiler Implementation

**Goal**: Implement the 11-stage ETL compiler as specified in the external agent's plan.

**Key Insight**: All metadata will be regenerated during compilation, fixing any inconsistencies in existing data. This approach eliminates the need for complex migration logic.

**Tasks:**

1. **Stage A — Load + Lint** (`etl/python/compile.py`):
   - JSON schema validation against existing `*.schema.json`
   - Uniqueness checks for IDs and synonyms
   - Transform normalization (merge duplicate IDs, keep lowest order)
   - Rule sanity checks (valid taxon/part prefixes, name_overrides exist)
   - Promoted parts validation (proto_path uses only part-changing TFs)
   - **Rules Normalization**: Apply `etl/python/lib/rules_normalize.py` to make rules forgiving
   - **Guarded Flags Validation**: Validate flag rules against transform/part definitions
   - **Output**: `build/report/lint.json`, `build/tmp/transforms_canon.json`, `build/tmp/flags.rules.validated.json`

   **Rules Normalizer Implementation** (`etl/python/lib/rules_normalize.py`):
   ```python
   # etl/python/lib/rules_normalize.py
   from typing import Dict, Any, Iterable, List

   def _strip_trailing_colon(s: str) -> str:
       return s[:-1] if s.endswith(":") else s

   def normalize_applies_to(at: Iterable[Any]) -> List[Dict[str, Any]]:
       out = []
       for item in at:
           if isinstance(item, str):
               out.append({"taxon_prefix": _strip_trailing_colon(item), "parts": []})
           elif isinstance(item, dict):
               tp = _strip_trailing_colon(item.get("taxon_prefix", ""))
               parts = [p if p.startswith("part:") else f"part:{p}" for p in item.get("parts", [])]
               out.append({"taxon_prefix": tp, "parts": sorted(set(parts))})
       # dedupe by (taxon_prefix, tuple(parts))
       uniq = {}
       for row in out:
           key = (row["taxon_prefix"], tuple(row["parts"]))
           uniq[key] = row
       return list(uniq.values())

   def normalize_transform_applicability(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
       normd = []
       for rec in records:
           rec = dict(rec)
           rec["transform"] = rec["transform"].strip()
           rec["applies_to"] = normalize_applies_to(rec.get("applies_to", []))

           # tofu edge: press applies to curd, not plant_milk
           if rec["transform"] == "tf:press":
               for row in rec["applies_to"]:
                   parts = row.get("parts", [])
                   if "part:plant_milk" in parts:
                       parts.remove("part:plant_milk")
                   if "part:curd" not in parts:
                       parts.append("part:curd")
                   row["parts"] = sorted(set(parts))

           normd.append(rec)
       return normd
   ```

   **Usage in Stage A**:
   ```python
   # etl/python/compile.py (Stage A)
   from lib.rules_normalize import normalize_transform_applicability

   raw = load_jsonl("data/ontology/rules/transform_applicability.jsonl")
   applicability = normalize_transform_applicability(raw)
   write_jsonl(applicability, f"{BUILD_TMP}/transform_applicability.normalized.jsonl")
   ```

   **Guarded Flags Validation** (`etl/python/lib/flags_validate.py`):
   ```python
   # etl/python/lib/flags_validate.py
   import re
   from typing import Dict, List, Tuple

   PARAM_RE = re.compile(r"^(tf:[a-z0-9_]+)\.([a-z0-9_.]+)$")

   def _index_transforms(tdefs: List[Dict]) -> Dict[str, Dict]:
       return {t["id"]: t for t in tdefs}

   def _param_exists(tdef: Dict, param_path: str) -> bool:
       # Supports dotted params like "cure.nitrite_ppm" (we store flat keys, so check first segment)
       first = param_path.split(".")[0]
       for p in tdef.get("params", []):
           if p.get("key") == first:
               return True
       return False

   def validate_guarded_flags(
       rules: List[Dict],
       transform_defs: List[Dict],
       part_ids: List[str]
   ) -> List[str]:
       """Shape already JSON-Schema validated. Here we do cross-reference checks."""
       errors: List[str] = []
       t_idx = _index_transforms(transform_defs)
       part_set = set(part_ids)

       for i, rule in enumerate(rules):
           loc = f"flags[{i}]"

           # has_transform
           def check_has_transform(obj: Dict):
               tid = obj["has_transform"]
               if tid not in t_idx:
                   errors.append(f"{loc}: unknown transform '{tid}'")

           # has_part
           def check_has_part(obj: Dict):
               pid = obj["has_part"]
               if pid not in part_set:
                   errors.append(f"{loc}: unknown part '{pid}'")

           # param cmp
           def check_param(obj: Dict):
               m = PARAM_RE.match(obj["param"])
               if not m:
                   errors.append(f"{loc}: bad param path '{obj['param']}'")
                   return
               tid, ppath = m.group(1), m.group(2)
               tdef = t_idx.get(tid)
               if not tdef:
                   errors.append(f"{loc}: param references unknown transform '{tid}'")
                   return
               if not _param_exists(tdef, ppath):
                   errors.append(f"{loc}: param '{ppath}' not in {tid}")

           def walk(group: List[Dict]):
               for cond in group:
                   if "has_transform" in cond: check_has_transform(cond)
                   elif "has_part" in cond: check_has_part(cond)
                   elif "param" in cond: check_param(cond)

           when = rule["when"]
           for key in ("allOf", "anyOf", "noneOf"):
               if key in when:
                   walk(when[key])

       return errors
   ```

   **Usage in Stage A**:
   ```python
   # etl/python/compile.py (Stage A)
   from jsonschema import Draft202012Validator
   from lib.flags_validate import validate_guarded_flags

   flag_rules = load_jsonl("data/ontology/rules/diet_safety_rules.jsonl")
   schema = load_json("data/sql/schema/flag_rule.schema.json")

   # 1) schema-level validation
   validator = Draft202012Validator(schema)
   for idx, rec in enumerate(flag_rules):
       for err in validator.iter_errors(rec):
           lint.add("flags-schema", f"flags[{idx}]: {err.message}")

   # 2) cross-ref validation
   transform_defs = load_json("data/ontology/transforms.json")  # merged base+overrides
   part_ids = [p["id"] for p in load_json("data/ontology/parts.json")]
   for msg in validate_guarded_flags(flag_rules, transform_defs, part_ids):
       lint.add("flags-xref", msg)

   write_json(f"{BUILD_TMP}/flags.rules.validated.json", {"count": len(flag_rules)})
   ```
   **Why**: The normalizer makes rules forgiving by handling trailing colons, normalizing taxon prefixes, and fixing the tofu press applicability edge case. This prevents E002 errors during compilation. The flags validation ensures all referenced transforms and parameters exist, preventing runtime errors during flag evaluation.

2. **Stage B — Substrate Graph (T×P)**:
   - Use `parts_applicability`, `taxon_part_policy`, `implied_parts` for substrate edges
   - Apply promoted parts with proto_path and byproduct edges
   - **Output**: `build/graph/substrates.jsonl`

3. **Stage C — Curated TPT Seed Ingestion**:
   - Load `derived_foods.jsonl` (curated TPTs)
   - Validate (taxon_id, part_id) in substrates
   - **Persist full path**: Store `path_full` before stripping non-identity transforms
   - Strip non-identity transforms from path[] (keep only identity + family-override transforms)
   - **Compute present_parts**: Start part + promoted proto yields + intermediates
   - Family assignment (explicit or pattern-matching)
   - **Output**: `build/tmp/tpt_seed.jsonl`

   **Implementation**:
   ```python
   # Stage C: Persist full path and compute present parts
   tpt["path_full"] = deepcopy(tpt["path"])
   family_identities = { fam["id"]: [t.replace("?", "") for t in fam["identity_transforms"]] }
   tpt["path"] = [s for s in tpt["path_full"] if s.get("identity", False) or s["id"] in family_identities.get(tpt["family_id"], [])]
   
   def compute_present_parts(taxon_id, part_id, proto_edges, path_full):
       s = {part_id}
       for e in proto_edges:  # from promoted_parts for this (taxon, part) if any
           s.add(e.get("yield_part"))
           for bp in e.get("byproducts", []): s.add(bp)
       # optional: add derived parts produced by explicit part-changing transforms in path_full
       return sorted(s)
   
   tpt["present_parts"] = compute_present_parts(tpt["taxon_id"], tpt["part_id"], proto_edges_for_tp, tpt["path_full"])
   ```

4. **Stage D — Family-Templated Expansions**:
   - Use `family_allowlist.jsonl` for eligible (taxon, part) substrates
   - Instantiate minimal identity paths from `families.json`
   - Controlled expansion (no parameter explosion)
   - **Output**: `build/tmp/tpt_generated.jsonl`

5. **Stage E — Canonicalization & IDs**:
   - Canonical path JSON (identity transforms only, sorted params)
   - **Param Buckets Precedence**: Family `param_buckets` override global `param_buckets.json`
   - Bucket numeric params via effective buckets (family overrides global)
   - Deterministic ID: `tpt:<taxon_slug>:<part_slug>:<family>:<pathHash>`
   - Collision detection with `~v2` suffix
   - **Output**: `build/tmp/tpt_canon.jsonl`

   **Implementation**:
   ```python
   # Stage E: Param buckets precedence (family overrides global)
   effective_buckets = {**global_buckets, **family.get("param_buckets", {})}
   ```

6. **Stage F — Names, Synonyms, and Display**:
   - Primary name resolution (curated → name_overrides → family template)
   - Synonym aggregation (curated + taxon_part_synonyms + part_aliases + family lexemes)
   - Cuisines/regions (seed or family defaults)
   - **Output**: `build/tmp/tpt_named.jsonl`

7. **Stage G — Derived Flags (Diet & Safety)**:
   - Use guarded flags system with `diet_safety_rules.jsonl`
   - Evaluate complex conditions with `allOf`/`anyOf`/`noneOf` operators
   - Check actual parameter values (e.g., `nitrite_ppm > 0`)
   - Dietary compatibility (vegan/vegetarian/pescetarian)
   - Safety flags (fermented, pasteurized, nitrite_present, smoked, retorted, raw_animal)
   - **Output**: merged back into `tpt_named.jsonl`

   **Flags Evaluator Implementation** (`etl/python/lib/flags_eval.py`):
   ```python
   # etl/python/lib/flags_eval.py
   from typing import Dict, List, Any, Set

   def _has_transform(path: List[Dict[str, Any]], tid: str) -> bool:
       return any(step.get("id") == tid for step in path)

   def _get_param(path: List[Dict[str, Any]], tid: str, pkey: str):
       for step in path:
           if step.get("id") == tid:
               params = step.get("params", {}) or {}
               # dotted keys allowed; we read first segment only (consistent with linter)
               first = pkey.split(".")[0]
               if first in params:
                   return params[first]
       return None

   def _cmp(op: str, lhs, rhs) -> bool:
       if op == "exists": return lhs is not None
       if op == "eq":     return lhs == rhs
       if op == "ne":     return lhs != rhs
       if op == "gt":     return (lhs is not None) and lhs > rhs
       if op == "gte":    return (lhs is not None) and lhs >= rhs
       if op == "lt":     return (lhs is not None) and lhs < rhs
       if op == "lte":    return (lhs is not None) and lhs <= rhs
       if op == "in":     return (lhs in (rhs or []))
       if op == "not_in": return (lhs not in (rhs or []))
       return False

   def evaluate_flags(
       rules: List[Dict[str, Any]],
       path_full: List[Dict[str, Any]],
       present_parts: Set[str]
   ) -> Dict[str, List[str]]:
       emitted = {"safety": [], "dietary": []}

       def test_group(group: List[Dict[str, Any]]) -> bool:
           for cond in group:
               if "has_transform" in cond:
                   if not _has_transform(path_full, cond["has_transform"]):
                       return False
               elif "has_part" in cond:
                   if cond["has_part"] not in present_parts:
                       return False
               elif "param" in cond:
                   tid, pkey = cond["param"].split(".", 1)
                   val = _get_param(path_full, tid, pkey)
                   if not _cmp(cond["op"], val, cond.get("value")):
                       return False
           return True

       for rule in rules:
           when = rule["when"]
           ok = True
           if "allOf" in when: ok = ok and test_group(when["allOf"])
           if "anyOf" in when: ok = ok and any(test_group([c]) for c in when["anyOf"])
           if "noneOf" in when: ok = ok and (not test_group(when["noneOf"]))
           if ok:
               emitted[rule["flag_type"]].append(rule["emit"])

       return emitted
   ```

   **Usage in Stage G**:
   ```python
   # etl/python/compile.py (Stage G)
   from lib.flags_eval import evaluate_flags

   rules = load_jsonl("data/ontology/rules/diet_safety_rules.jsonl")
   flags = evaluate_flags(rules, tpt["path_full"] or tpt["path"], set(tpt["present_parts"]))
   tpt["safety_flags"] = sorted(set(flags["safety"]))
   tpt["dietary_compat"] = sorted(set(flags["dietary"]))
   ```
   **Why**: The guarded flags system provides more accurate and maintainable flag evaluation than simple mapping. It supports complex conditions and parameter-aware logic, ensuring flags are only emitted when conditions are actually met.

8. **Stage H — Graph Edges**:
   - T --has_part--> P
   - P --yields--> PromotedPart (from byproducts)
   - P --transforms_to--> TPT (identity path only)
   - TPT --in_family--> Family
   - **Output**: `build/graph/edges.jsonl`

9. **Stage I — TPT Meta (Final UI Payload)**:
   - Denormalized "card blob" per TPT for direct API/UI consumption
   - Include upstream/related rails, search boost factors
   - **Output**: `build/out/tpt_meta.jsonl`

10. **Stage J — Search Docs (Neutral to FTS Architecture)**:
    - Three doc types: TAXON_PART (TP), TPT, PART (promoted parts)
    - Unified or sharded FTS support
    - **Output**: `build/out/search_docs.jsonl`

11. **Stage K — API Wire Shapes**:
    - Navigation data for sidebar/grouping
    - Families catalog for family landing pages
    - **Output**: `build/out/navigation.json`, `build/out/families_catalog.json`

### 2.3 Error Handling & Validation

**Goal**: Implement comprehensive error handling and validation as specified.

**Tasks:**

1. **Error Classes** (fail closed on E001-E004 for curated TPTs):
   - **E001**: Invalid TF in path (not identity, or not applicable)
   - **E002**: Missing substrate edge (T×P)
   - **E003**: Family not resolvable from path
   - **E004**: Promoted part uses identity TF in `proto_path`
   - **E005**: Duplicate ID collision (resolved with `~v2`, but logged)
   - **E006**: Unsafe/ambiguous dietary flag inference (falls back to unknown)

2. **Validation Rules**:
   - Every rule `applies_to` refers to valid taxon/part prefixes
   - Every `name_overrides` pair exists
   - Every `promoted_parts.proto_path` uses only **part-changing TFs**
   - All TFs used in `proto_path` or `path` must be allowed for `(taxon, part)`
   - `identity_params ⊆ path.params`
   - Family must declare ≥1 identity param

3. **Incremental & Determinism**:
   - Compiler digests input file mtimes + content hash
   - Rebuild only affected families/parts
   - IDs remain stable (based on canonical path)
   - "Golden set" tests: bacon, pancetta, yogurt/Greek/labneh, tofu, ghee, EVOO vs refined oil, kimchi/sauerkraut

### 2.4 TPT Meta Schema & Identity Hash

**Goal**: Implement TPT identity hashing and final UI payload schema.

**Key Insight**: Identity hashing must be deterministic and stable. Only identity parameters contribute to the hash, ensuring that minor process variations don't create new identities.

**Tasks:**

1. **TPT Meta Schema** (final UI payload):
   ```json
   {
     "id": "tpt:bos_taurus:milk:yogurt",
     "stable_id": "tpt:bos_taurus:milk:CULTURED_DAIRY:3K2PH1Q9",
     "identity_hash": "3K2PH1Q9",
     "name": "Yogurt",
     "taxon_id": "tx:...:bos:taurus",
     "taxon_display": "Cow",
     "part_id": "part:milk",
     "part_display": "Milk",
     "family_id": "CULTURED_DAIRY",
     "path": [
       {"id":"tf:ferment","params":{"starter":"yogurt_thermo"}}
     ],
     "path_tokens": ["fermented", "thermophilic"],
     "identity_params": {"starter":"yogurt_thermo"},
     "cuisines": ["Global"],
     "regions": [],
     "synonyms": ["Yoghurt","Dahi"],
     "dietary_compat": ["vegetarian"],
     "safety_flags": ["fermented"],
     "upstream": {"taxon_part":"Cow Milk"},
     "related": {"siblings_in_family":["Greek Yogurt","Labneh"]},
     "search_boost": {"family":1.2,"canonical_name":1.0}
   }
   ```
   **ID Strategy**: 
   - `id`: Human-readable slug for stable URLs
   - `stable_id`: Primary key with family and hash for joins
   - `identity_hash`: Separate field for deduplication

2. **Identity Hash Implementation** (with family overrides):
   ```python
   def generate_tpt_identity_hash(taxon_id, part_id, path, family=None, family_identities=None):
       fam_ids = set()
       if family and family_identities:
           fam_ids = set(family_identities.get(family, []))  # e.g., ["tf:ferment","tf:strain"]

       canonical_path = []
       for step in path:
           tid = step['id']
           is_identity = step.get('identity', False) or (tid in fam_ids)
           if not is_identity:
               continue
           # keep only identity_params (marking still honored)
           params = step.get('params', {}) or {}
           keep = {}
           for k, v in params.items():
               # treat family-declared transforms as identity: keep all marked identity_param OR
               # allow families to name naked params (e.g., "strain_level") in their identity_params
               if step.get('param_specs', {}).get(k, {}).get('identity_param', False):
                   keep[k] = v
           canonical_path.append({"id": tid, "params": keep, "order": step.get("order", 999)})

       canonical_path.sort(key=lambda x: x["order"])
       normalized = {"taxon_id": taxon_id, "part_id": part_id, "path": canonical_path}
       return base32(sha1(json.dumps(normalized, sort_keys=True)))[:8]
   ```

   **Compiler input**: Build family identities dict from `families.json`:
   ```python
   family_identities = { fam["id"]: [t.replace("?", "") for t in fam["identity_transforms"]] }
   ```
   **Why**: Family overrides allow `tf:strain` to be identity-bearing only for CULTURED_DAIRY family, enabling Greek/Labneh variants while keeping strain non-identity globally.

3. **Search Docs Schema** (aligned doc types):
   ```json
   // TAXON_PART (TP)
   {
     "id": "tp:bos_taurus:milk",
     "type": "tp",
     "primary": "Cow Milk",
     "tokens": ["cow", "milk", "dairy"],
     "facets": {"kingdom": "animalia", "part_category": "secreted"},
     "links": {"tpt_children": ["CULTURED_DAIRY", "CHEESE"]}
   }
   
   // TPT
   {
     "id": "tpt:...",
     "type": "tpt",
     "primary": "Bacon",
     "alt": ["streaky bacon", "smoked pork belly"],
     "family": "DRY_CURED_MEAT",
     "path_str": "cure(dry,nitrite) -> smoke(cold)",
     "cuisines": ["American", "British"],
     "diet": ["non_vegetarian"],
     "safety": ["smoked", "nitrite_present"],
     "substrate": "Pork Belly",
     "tokens": ["pork", "belly", "cured", "smoked"],
     "sort": {"family_rank": 2, "substrate_rank": 1}
   }
   
   // PART (promoted parts)
   {
     "id": "part:butter",
     "type": "part",
     "primary": "Butter",
     "proto_path": "separate -> churn",
     "byproducts": ["Buttermilk"],
     "tokens": ["cream", "butter", "dairy", "fat"],
     "links": {"tpt_children": ["Ghee", "Brown Butter"]}
   }
   ```

### 2.5 Golden Test Suite

**Goal**: Implement comprehensive validation tests to catch regressions and ensure data integrity.

**Key Insight**: Golden tests validate the entire pipeline end-to-end, catching both ontology drift and compiler bugs. They use canonical examples that represent key patterns in the system.

**Tasks:**

1. **Create Golden Test Suite** (`etl/tests/test_golden_tpt.py`):
   - Validates transform normalization (smoke.mode, cure.style, cure.nitrite_ppm)
   - Tests canonical TPTs: bacon, sauerkraut, tofu, EVOO vs refined oil
   - Ensures conditional safety flags work correctly
   - Validates identity hashing stability

2. **Test Assertions**:
   - **Bacon**: has `tf:cure` with `nitrite_ppm > 0` and `tf:smoke` with `mode == "cold"`
   - **Sauerkraut**: has `tf:salt` then `tf:ferment`, carries `fermented` flag
   - **Tofu**: substrate is `part:plant_milk`, has `tf:coagulate` + `tf:press`
   - **Oil split**: EVOO has no `tf:refine_oil`, refined oil has `tf:refine_oil`
   - **Transform normalization**: `tf:smoke` uses `mode` param, `tf:cure` uses `style` and `nitrite_ppm`

3. **CI Integration**:
   - Run tests after ETL compilation
   - Fail loudly on any regression
   - Provide clear error messages pointing to specific issues
   - **Why**: End-to-end validation catches both ontology drift and compiler bugs that unit tests might miss. Golden tests ensure the entire pipeline works correctly with real data.

4. **Sample Test Data** (add to `derived_foods.jsonl`):
   ```jsonl
   {"id":"tpt:suidae:belly:bacon","taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus","part_id":"part:cut:belly","transforms":[{"id":"tf:cure","params":{"style":"dry","nitrite_ppm":120}},{"id":"tf:smoke","params":{"mode":"cold"}}],"name":"Bacon","synonyms":["streaky bacon"]}
   {"id":"tpt:brassica:capitata:leaf:sauerkraut","taxon_id":"tx:plantae:brassicaceae:brassica:oleracea:capitata","part_id":"part:leaf","transforms":[{"id":"tf:salt","params":{"method":"dry","salt_pct":2.0}},{"id":"tf:ferment"}],"name":"Sauerkraut"}
   {"id":"tpt:olea_europaea:expressed_oil:evoo","taxon_id":"tx:plantae:oleaceae:olea:europaea","part_id":"part:expressed_oil","transforms":[{"id":"tf:press"}],"name":"Extra Virgin Olive Oil","synonyms":["EVOO"]}
   {"id":"tpt:olea_europaea:expressed_oil:refined","taxon_id":"tx:plantae:oleaceae:olea:europaea","part_id":"part:expressed_oil","transforms":[{"id":"tf:press"},{"id":"tf:refine_oil"}],"name":"Refined Olive Oil"}
   ```

---

## Phase 3: API Layer (Week 3)

**Note**: This phase will involve breaking changes to existing API contracts. The UI will be updated to match new interfaces.

### 3.1 Unified Search API

**Goal**: Implement the unified search across T/TP/TPT nodes using the new ETL deliverables.

**Tasks:**

1. **Update `search.combined`** endpoint to use `build/out/search_docs.jsonl`:
   ```typescript
   search: t.router({
     combined: t.procedure
       .input(z.object({
         q: z.string(),
         docTypes: z.array(z.enum(['tp', 'tpt', 'part'])).optional(),
         filters: z.object({
           partCategory: z.string().optional(),
           family: z.string().optional(),
           cuisines: z.array(z.string()).optional(),
           dietary: z.array(z.string()).optional(),
           safety: z.array(z.string()).optional()
         }).optional(),
         limit: z.number().default(20)
       }))
       .query(({ input }) => {
         // Load from build/out/search_docs.jsonl
         // Apply FTS search with BM25 ranking
         // Apply doc_type boosting (TPT for commodity terms, TP for part terms)
         // Apply family and facet filters
         // Return mixed results with badges
       })
   })
   ```
   **Breaking Change**: This replaces the current `kinds` parameter with `docTypes` and changes the response structure. UI will be updated accordingly. **Note**: API uses `['tp', 'tpt', 'part']` to match emitted corpus; taxon docs can be added later if needed.

2. **Search Ranking Logic**:
   - Exact name match > synonym > alias > token overlap
   - Doc type boosting (TPT for commodity terms, TP for part terms, T for species terms)
   - Family ranking (from `sort.family_rank`)
   - Substrate ranking (from `sort.substrate_rank`)
   - Search boost factors (from `search_boost`)

3. **FTS Architecture Support**:
   - **Unified FTS**: Single index with `type` facet for all doc types
   - **Sharded FTS**: Three separate indexes (T, TP, TPT) with API merging
   - Support both approaches via configuration
   - **FTS Complexity**: This is intentionally complex to provide a cleaner interface for API and UI. Unified search eliminates the need for complex merging logic and provides consistent ranking across all node types.

### 3.2 Food Node Lookup API

**Goal**: Implement detailed food node lookup using ETL deliverables.

**Tasks:**

1. **Add `foodNodes.getById`** endpoint using `build/out/tpt_meta.jsonl`:
   ```typescript
   foodNodes: t.router({
     getById: t.procedure
       .input(z.object({ id: z.string() }))
       .query(({ input }) => {
         // Load from build/out/tpt_meta.jsonl for TPT
         // Load from build/out/search_docs.jsonl for TP/T
         // Return normalized node payload with upstream/related rails
         // Include neighbor panel for TPT (siblings_in_family)
         // Include applicable transforms for TP
       })
   })
   ```

2. **Browse Endpoints** using ETL deliverables:
   - `GET /taxa/:taxonId/parts` → top TPs from `build/graph/substrates.jsonl`
   - `GET /taxa/:taxonId/derived?partId=part:milk&family=CULTURED_DAIRY` → curated TPTs
   - `GET /families` → family catalog from `build/out/families_catalog.json`
   - `GET /families/:familyId` → family page with shared facets

3. **Navigation Endpoints**:
   - `GET /navigation` → sidebar/grouping data from `build/out/navigation.json`
   - `GET /suggest?seedId=:id` → related nodes from graph edges

4. **Compile TPT Endpoint**:
   - `POST /compile-tpt` for power users and ETL validation
   - Returns canonical identity hash and diff to nearest curated TPT
   - Uses same canonicalization logic as ETL compiler

### 3.3 Suggestion API

**Goal**: Implement related node suggestions.

**Tasks:**

1. **Add `suggest.related`** endpoint:
   ```typescript
   suggest: t.router({
     related: t.procedure
       .input(z.object({ seedId: z.string() }))
       .query(({ input }) => {
         // Find related nodes based on:
         // - Same taxon (different parts)
         // - Same part (different taxa)
         // - Similar transform paths
         // - Popular combinations
       })
   })
   ```

---

## Phase 4: UI Enhancements (Week 4)

**Note**: This phase will involve significant UI changes to support the new TPT system and unified search interface.

### 4.1 Unified Search Interface

**Goal**: Implement the unified search UI with mixed results and family-based grouping.

**Tasks:**

1. **Update Search Component**:
   - Mixed results list with badges ("Derived", "Part", "Taxon")
   - Transform path chips for TPT results (identity steps only)
   - Filter sidebar (Part kind, Family, Cuisine, "Only derived foods")
   - Intent-based result ordering with family grouping

2. **Search Result Cards** (following card anatomy from vision):
   - **TPT Card**: 
     - Label + breadcrumb: `Taxon ▶ Part ▶ TPT`
     - Path chips (identity steps only): e.g., `cure (dry, nitrite) → smoke (cold)`
     - Badges from safety/diet flags: `fermented`, `smoked`, `nitrite-free`, `pasteurized`, `vegan`
     - Metadata chips: `family_id`, `cuisines`, `regions`
     - "How it's made" expand → humanized path from `path[]`
     - "From this" & "Related" rails: upstream Part; sibling TPTs in same family
   - **Part Card**:
     - Label + breadcrumb: `Taxon ▶ Part` (for promoted parts, show "made by: separate→churn" hint)
     - "Common derived foods" rail → top TPTs from this substrate
     - Light tags: `cuisines`, `regions` if present
   - **Taxon Card**: Show common parts, popular derived foods

### 4.2 Enhanced Entity Pages

**Goal**: Implement rich entity pages for each node type with family-based organization.

**Tasks:**

1. **Taxon Pages** (e.g., Cow):
   - "Common parts" (TP grid)
   - "Popular derived foods" (TPT grid) grouped by family
   - Cross-taxon suggestions ("Try with goat")

2. **Part Pages** (e.g., Milk):
   - Surface **top family groupings** (CULTURED_DAIRY, CHEESE families)
   - Group TPTs by family with shared facet blocks for identity params
   - Transform chips for filtering within families
   - Process flow visualization

3. **Family Pages** (e.g., CULTURED_DAIRY):
   - Shared facet blocks for identity params (e.g., starter, strain level)
   - TPT grid organized by taxon/part
   - Family-specific filtering and exploration

4. **TPT Pages** (e.g., Bacon):
   - Hero with name, synonyms, badges
   - Transform timeline with identity params only
   - Variants rail (Pancetta, Guanciale) - sibling TPTs in same family
   - "Swap taxon/part" suggestions
   - "From this" & "Related" rails: upstream Part; sibling TPTs in same family

### 4.3 Builder Mode

**Goal**: Implement advanced TPT builder with snapping.

**Tasks:**

1. **TPT Builder Component**:
   - Start from TP with "Add transforms" tray
   - Real-time validation and snapping to curated TPTs
   - Transform parameter forms with identity marking
   - Preview of canonical path

2. **Snapping Logic**:
   - Detect when user input matches existing TPT
   - Show "Looks like Greek yogurt → open card" suggestions
   - Highlight differences in parameters

### 4.4 Core Pivots & Navigation

**Goal**: Implement the three core navigation patterns from the vision.

**Tasks:**

1. **By Base (Taxon→Part)**:
   - Start from salmon fillet / cow milk / soy milk / wheat flour
   - Part pages surface top family groupings
   - "Common derived foods" rail for each part

2. **By Family**:
   - Explore CULTURED_DAIRY, DRY_CURED_MEAT, VIRGIN_OIL, etc.
   - Family pages with shared facet blocks for identity params
   - TPT grid organized by taxon/part within family

3. **By Product (TPT)**:
   - Direct lookup of "bacon", "Greek yogurt", "ghee"
   - TPT pages with full context and variants
   - Search result grouping by family, then by taxon/part

### 4.5 Contextual Surfacing

**Goal**: Implement contextual suggestions throughout the UI.

**Tasks:**

1. **TP Page Banners**:
   - "Common derived foods from this part" when landing on TP
   - Ranked TPT chips with quick actions

2. **TPT Page Context**:
   - "Upstream" (TP & Taxon) navigation
   - "Downstream variants" (sibling TPTs in same family)
   - Related taxa suggestions

3. **Disambiguation UI**:
   - Compact chooser for ambiguous queries
   - "Do you mean the fish (Taxon), fillet (Part) or smoked salmon (Derived)?"

---

## Phase 5: Governance & Analytics (Week 5)

### 5.1 Curation Governance

**Goal**: Implement governance and validation for TPT curation.

**Tasks:**

1. **Linter Implementation**:
   - Validate TPT ID format
   - Check transform applicability
   - Verify identity parameter usage
   - Ensure required fields (name, synonyms, rationale)

2. **PR Labels & Workflow**:
   - `derived:add`, `derived:edit`, `derived:deprecate` labels
   - Required rationale for new TPTs
   - Automated validation in CI

3. **Curation Guidelines**:
   - Document boundary rules (Part vs TPT vs promoted Part)
   - Provide decision checklist for new entries
   - Establish review process for edge cases

### 5.2 Analytics & Telemetry

**Goal**: Implement analytics for search optimization and curation.

**Tasks:**

1. **Search Analytics**:
   - Track search → click → node ID patterns
   - Monitor CTR by doc type and ranking position
   - Identify popular search terms without results

2. **Ranking Optimization**:
   - A/B test doc type boosts
   - Tune transform familiarity penalties
   - Optimize based on user engagement

3. **Curation Insights**:
   - Identify high-engagement TPTs for promotion
   - Flag low-engagement TPTs for review
   - Suggest new TPTs based on search patterns

### 5.3 Performance & Monitoring

**Goal**: Ensure system performance and reliability.

**Tasks:**

1. **Performance Optimization**:
   - FTS query optimization
   - Caching for popular searches
   - Database indexing for edge queries

2. **Monitoring & Alerting**:
   - Search latency monitoring
   - Error rate tracking
   - Database performance metrics

3. **Load Testing**:
   - Test unified search under load
   - Validate FTS performance with large catalogs
   - Ensure responsive UI with mixed results

---

## Phase 6: Expansion & Polish (Week 6)

### 6.1 Catalog Expansion

**Goal**: Expand curated TPT catalog based on usage patterns.

**Tasks:**

1. **High-Impact Additions**:
   - Grains & bakery (bread, pasta, crackers)
   - Sweets & confections (chocolate, candy)
   - Beverages (wine, beer, kombucha)
   - Spices & seasonings

2. **Regional Specialties**:
   - Asian cuisines (miso, tempeh, kimchi variants)
   - European specialties (cheese varieties, cured meats)
   - Latin American (fermented corn, chiles)

3. **Part Promotion Candidates**:
   - Evaluate TPTs for promotion to derived parts
   - Implement promotion workflow
   - Update downstream references

### 6.2 Advanced Features

**Goal**: Implement advanced features for power users.

**Tasks:**

1. **Semantic Search**:
   - Integrate embeddings for semantic similarity
   - Blend with lexical search results
   - Improve handling of synonyms and related terms

2. **Advanced Filtering**:
   - Cuisine/region filters
   - Dietary restriction filters
   - Process complexity filters

3. **Export & Integration**:
   - API for external integrations
   - Data export formats
   - Webhook notifications for changes

### 6.3 Documentation & Training

**Goal**: Complete documentation and user training materials.

**Tasks:**

1. **User Documentation**:
   - Search guide with examples
   - TPT builder tutorial
   - API documentation

2. **Curator Training**:
   - Boundary rules guide
   - Curation best practices
   - Quality assurance checklist

3. **Developer Documentation**:
   - Architecture overview
   - Extension points
   - Performance guidelines

---

## Success Metrics

### Phase 1-2 (Foundation)
- ✅ All missing transforms and parts added
- ✅ TPT catalog with 25+ curated foods
- ✅ Unified food nodes schema implemented
- ✅ ETL pipeline updated and tested

### Phase 3-4 (API & UI)
- ✅ Unified search working across T/TP/TPT
- ✅ Rich entity pages for all node types
- ✅ TPT builder with snapping
- ✅ Contextual suggestions throughout UI

### Phase 5-6 (Governance & Polish)
- ✅ Linter and governance in place
- ✅ Analytics and ranking optimization
- ✅ Performance monitoring and optimization
- ✅ Expanded catalog with 100+ TPTs

### Long-term Goals
- **User Experience**: Users can find familiar foods (TPT) instantly while discovering underlying biology
- **Curation Quality**: High-quality, culturally accurate derived foods with clear provenance
- **System Performance**: Sub-100ms search response times with unified FTS
- **Extensibility**: Clear patterns for adding new TPTs and promoting parts
- **Analytics**: Data-driven optimization of search ranking and curation

---

## Risk Mitigation

### Technical Risks
- **FTS Performance**: Implement proper indexing and query optimization
- **Data Consistency**: Robust validation and linting prevent inconsistencies
- **Migration Complexity**: Phased rollout with backward compatibility

### Product Risks
- **User Confusion**: Clear UI patterns and badges distinguish node types
- **Curation Quality**: Governance and review process ensure accuracy
- **Performance**: Monitoring and optimization prevent degradation

### Operational Risks
- **Maintenance Overhead**: Automated validation and clear patterns reduce burden
- **Scalability**: Unified architecture scales better than separate systems
- **Data Quality**: Linting and governance prevent quality issues

---

## Conclusion

This implementation plan delivers the unified T/TP/TPT food node system as envisioned, building on our existing TP foundation while adding the curated TPT layer. The phased approach ensures low-risk delivery while providing immediate user value through better search and discovery.

The result will be a coherent, scalable system where users can find familiar foods instantly while exploring the underlying biological and processing logic that defines them.

---

## Additional Implementation Notes

### **Specific Fixes Needed**

1. **`composeFoodState` Refactor**: Current function enforces identity-only transforms but needs update for TPT identity hashing. The new approach with `identity_param` flags provides better granular control.

2. **Build Structure**: Using `/build` for ETL artifacts and `/dist` for TypeScript assets is by design. This maintains clear separation between build products.

3. **API Contract Changes**: Breaking changes to search endpoints (`kinds` → `docTypes`) and response structures are acceptable. UI will be updated to match.

4. **Data Regeneration**: All metadata will be regenerated during compilation, eliminating the need for complex migration logic.

5. **FTS Architecture**: Unified search is intentionally complex to provide cleaner API/UI interfaces and consistent ranking.

---

## ETL Deliverables Summary

### **Primary Deliverables** (what API/UI consumes immediately)

1. **`build/out/tpt_meta.jsonl`** — Canonical TPT cards (phase-1 UI ready)
   - Complete TPT metadata with upstream/related rails
   - Search boost factors and family relationships
   - Ready for direct API consumption

2. **`build/out/search_docs.jsonl`** — Neutral search corpus
   - Three doc types: TAXON_PART (TP), TPT, PART (promoted parts)
   - Works for unified or sharded FTS architecture
   - Includes ranking hints and facet data

3. **`build/out/navigation.json`** — Navigation data for sidebar/grouping
4. **`build/out/families_catalog.json`** — Family landing pages data
5. **`build/graph/edges.jsonl`** — Graph edges for navigation rails
6. **`build/graph/substrates.jsonl`** — T×P substrate relationships

### **What the API & UI Get "For Free"**

- **Upstream/related rails** on TP and TPT pages (from edges)
- **Family pages** backed by `families_catalog.json`, with shared facets from `identity_params`
- **Badges** (diet/safety) computed, consistent, and cheap to render
- **Stable IDs** → safe to bookmark/cache
- **Search optimization** with pre-computed ranking factors
- **Family-based organization** throughout the UI
- **Deterministic naming** with cultural accuracy
- **Comprehensive validation** with clear error reporting

### **Golden Set Tests** (compiler validation)

The ETL compiler will validate against these canonical examples:
- **Bacon** (DRY_CURED_MEAT family)
- **Pancetta** (DRY_CURED_MEAT family variant)
- **Yogurt/Greek/Labneh** (CULTURED_DAIRY family progression)
- **Tofu** (promoted part with downstream TPTs)
- **Ghee** (BUTTER_DERIVATIVES family)
- **EVOO vs Refined Oil** (VIRGIN_OIL vs REFINED_OIL families)
- **Kimchi/Sauerkraut** (BRINED_FERMENT_VEG family)

This comprehensive ETL compiler provides a production-ready foundation for the unified T/TP/TPT food node system, with all the specificity needed for confident implementation.


