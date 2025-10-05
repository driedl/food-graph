# Ontology Inconsistencies & Patterns

This document tracks inconsistencies found in the food graph ontology and suggests patterns for improvement.

## Current Inconsistencies

### 1. Duplicate Parts

#### Liver Parts
- `part:organ:liver` (line 80) - "Liver" with kind "animal" ✅ **Keep this one**
- `part:liver` (line 235) - "Liver" with kind "animal" ❌ **Remove - duplicate**

#### Egg Parts
- `part:egg_white` (line 37) - "Egg white (albumen)" with kind "animal" ❌ **Remove - legacy**
- `part:egg:white` (line 255) - "Egg white" with kind "bird" with parent_id "part:egg" ✅ **Keep this one**
- `part:egg_yolk` (line 45) - "Egg yolk" with kind "animal" ❌ **Remove - legacy**
- `part:egg:yolk` (line 261) - "Egg yolk" with kind "bird" with parent_id "part:egg" ✅ **Keep this one**

### 2. Incomplete Hierarchies

#### Dairy Hierarchy
- `part:cream` has `parent_id: "part:milk"` ✅ **Correct**
- `part:curd` has NO parent_id ❌ **Should be child of part:milk**
- `part:whey` has NO parent_id ❌ **Should be child of part:milk**
- `part:butter` has NO parent_id ❌ **Should be child of part:milk**
- `part:buttermilk` has NO parent_id ❌ **Should be child of part:milk**

#### Plant Grain Hierarchy
- `part:bran` has NO parent_id ❌ **Should be child of part:grain**
- `part:germ` has NO parent_id ❌ **Should be child of part:grain**
- `part:endosperm` has NO parent_id ❌ **Should be child of part:grain**
- `part:hull` has NO parent_id ❌ **Should be child of part:grain**

#### Citrus Fruit Hierarchy
- `part:peel` has NO parent_id ❌ **Should be child of part:fruit (for citrus)**
- `part:pith` has NO parent_id ❌ **Should be child of part:fruit (for citrus)**
- `part:flavedo` has NO parent_id ❌ **Should be child of part:fruit (for citrus)**

#### Animal Parts Hierarchy
- `part:marrow` has NO parent_id ❌ **Should be child of part:bone**
- `part:fat:leaf` has parent_id ❌ **Should be child of part:fat**
- `part:fat:subcutaneous` has NO parent_id ❌ **Should be child of part:fat**

### 3. Inconsistent Kind Values

#### Egg Parts
- `part:egg` has `kind: "bird"` ❌ **Should be "animal" + category: "egg"**
- `part:egg_white` has `kind: "animal"` ❌ **Should be "animal" + category: "egg"**
- `part:egg_yolk` has `kind: "animal"` ❌ **Should be "animal" + category: "egg"**

**Resolution:** Use `kind: "animal"` + `category: "egg"` for all egg parts. The `category` field provides specificity while keeping `kind` biological. Scope by taxon via applicability rules.

### 4. Inconsistent Naming Patterns

#### Current Patterns
- **Hierarchical:** `part:organ:liver`, `part:cut:brisket`, `part:fat:leaf`
- **Flat:** `part:liver`, `part:muscle`, `part:bone`
- **Legacy:** `part:egg_white` vs `part:egg:white`

#### Suggested Standard Pattern
```
part:{category}:{specific}
```

Where categories include:
- `organ` - internal organs
- `cut` - meat cuts
- `fat` - fat types
- `egg` - egg types
- `grain` - grain components
- `fruit` - fruit components

## Suggested Patterns

### 1. Hierarchical Naming Convention
```
part:{category}:{specific}
```

Examples:
- `part:organ:liver`
- `part:cut:brisket`
- `part:fat:leaf`
- `part:egg:white`
- `part:grain:bran`

### 2. Kind Values
- `animal` - general animal parts
- `plant` - general plant parts
- `fungus` - fungus-specific parts
- `derived` - processed/derived products

**Note:** Use `category` field for specificity (e.g., `category: "egg"`, `category: "cut"`, `category: "dairy"`). Scope by taxon via applicability rules rather than using taxonomic categories as `kind` values.

### 3. Hierarchy Rules
- Parent parts should have broader applicability
- Child parts inherit parent applicability
- Only apply parent parts to taxa, not children
- Use `parent_id` to establish relationships

### 4. Egg Taxonomy Considerations

**Research needed:** Do humans consume eggs from non-bird species?

If yes, consider this hierarchy:
```
part:egg (kind: "animal", category: "egg", applies_to: [all egg-laying animals])
├── part:egg:bird (kind: "animal", category: "egg", parent_id: "part:egg")
├── part:egg:reptile (kind: "animal", category: "egg", parent_id: "part:egg")
└── part:egg:fish (kind: "animal", category: "egg", parent_id: "part:egg")
    └── part:egg:fish:roe (kind: "animal", category: "egg", parent_id: "part:egg:fish")
```

**Note:** Caviar is a processed product (salted roe), not an anatomical part. Model caviar as a TPT with `tf:salt` transform on `part:egg:fish:roe`.

## Action Items

### ✅ Completed
1. **ETL2 Validation Integration** - Implemented comprehensive validation system
2. **Schema Compliance Validation** - Catches kind field violations
3. **Duplicate Detection** - Ready to catch duplicate parts and transforms
4. **Hierarchy Validation** - Ready to catch missing parent relationships
5. **Parameter Consistency** - Ready to catch family/transform mismatches
6. **Categories Database Integration** - Full Stage F integration with 32 categories and 66 parts
7. **Transaction Timing Fixes** - Resolved foreign key constraint issues
8. **Part Dependency Resolution** - Implemented topological sort for parent-child relationships

### 🔥 Critical Fixes (Immediate)
1. **Fix Transform Parameter Validation** - Add enum validation and Stage F checks
2. **Fix Stage F Validation Issues** - Parameter drift, flag evaluation, cycle detection
3. **Add Comprehensive TPT Examples** - Edge-case exemplars for testing

## Implementation Progress

### ✅ Phase 1.1: Critical Schema & Data Fixes (COMPLETED)

**Date**: December 2024  
**Status**: ✅ COMPLETED - ETL2 pipeline now passes with 0 errors

#### Schema Violations Fixed
- ✅ **part.schema.json** - Added `"derived"` to kind enum and `category` field
- ✅ **transform.schema.json** - Added missing `order` field
- ✅ **Kind Values** - Fixed `kind: "bird"` → `kind: "animal"` + `category: "egg"` for all egg parts

#### Duplicate Parts Removed
- ✅ **part:liver** - Removed duplicate of `part:organ:liver`
- ✅ **part:egg_white** - Removed duplicate of `part:egg:white`
- ✅ **part:egg_yolk** - Removed duplicate of `part:egg:yolk`

#### Parent Relationships Added (Bible-Compliant)
- ✅ **Grain hierarchy**: `part:bran`, `part:germ`, `part:endosperm` → `part:grain`
- ✅ **Dairy hierarchy**: `part:curd`, `part:whey` → `part:milk`
- ✅ **Dairy hierarchy**: `part:butter`, `part:buttermilk` → `part:cream` (Bible-compliant!)
- ✅ **Animal hierarchy**: `part:marrow` → `part:bone`

#### Validation Rules Updated
- ✅ **COMMON_MISSING_PARENTS** - Updated to match Ontology Bible hierarchy
- ✅ **Bible Alignment** - Fixed butter/buttermilk to use cream→milk instead of direct milk

**Result**: ETL2 pipeline passes completely with 0 validation errors.

### ✅ Phase 1.2: Transform Parameter Fixes (COMPLETED)

**Date**: December 2024  
**Status**: ✅ COMPLETED - All transform parameter mismatches resolved

#### Transform Parameter Mismatches Fixed
- ✅ **tf:strain** - Fixed `target_TS_pct` → `strain_level` parameter naming (2 occurrences)
- ✅ **tf:clarify** - Fixed `tf:clarify` → `tf:clarify_butter` ID mismatch (2 occurrences)

#### Transform ID Mismatches Fixed
- ✅ **Family references** - Updated families.json to use correct transform IDs
- ✅ **Parameter consistency** - All parameter names now match across files

**Result**: ETL2 pipeline continues to pass with 0 errors.

### ✅ Phase 1.3: Product-Part Anchoring (COMPLETED)

**Date**: December 2024  
**Status**: ✅ COMPLETED - Split registry architecture implemented

#### Product Parts Implementation
- ✅ **parts.derived.jsonl** - Created with 16 derived product parts
- ✅ **Split registry architecture** - Stage 0 merges core + derived into parts.registry.json
- ✅ **part_ancestors table** - Implemented in Stage F with transitive closure (103 entries, max depth 3)
- ✅ **Bible-compliant hierarchy** - butter → cream → milk ancestry working correctly

#### Registry Architecture
- ✅ **Core parts** (50) - Biological/anatomical parts in parts.json
- ✅ **Derived parts** (16) - Product parts in parts.derived.jsonl with kind="derived"
- ✅ **Merged registry** - Single authoritative parts.registry.json for downstream stages
- ✅ **Backward compatibility** - parts.json created for existing code

**Result**: ETL2 pipeline passes with 66 total parts (50 core + 16 derived).

### ✅ Phase 1.4: Enhanced Validation & Metadata (COMPLETED)

**Date**: December 2024  
**Status**: ✅ COMPLETED - All metadata files added and validated

#### Metadata Additions
- ✅ **Family metadata** - Added family_meta.json with UI labels, icons, colors for 10 families
- ✅ **Diet/safety rules** - Added diet_safety_rules.jsonl with 10 comprehensive flag evaluation rules
- ✅ **Cuisine mappings** - Added cuisine_map.jsonl with cultural context for 10 food categories
- ✅ **Schema compliance** - Fixed Stage A to read from merged parts registry
- ✅ **Flag validation** - All rules pass validation with proper schema format

#### Validation Enhancements
- ✅ **Split registry integration** - Stage A now reads from parts.registry.json
- ✅ **Flag rule validation** - 10 rules validated against transform and part references
- ✅ **Schema compliance** - All metadata files follow proper JSON schema

**Result**: ETL2 pipeline passes with complete metadata integration.

### ✅ Phase 1.5: Category Ontology Implementation (COMPLETED)

**Date**: December 2024  
**Status**: ✅ COMPLETED - Proper ontology-driven category system implemented

#### Category Ontology Architecture
- ✅ **categories.json** - Created authoritative registry with 32 categories
- ✅ **Rich metadata** - Each category has `id`, `name`, `description`, `kind`
- ✅ **Self-validating** - Validators read from ontology file, preventing data drift
- ✅ **Schema integration** - `part.schema.json` references categories.json
- ✅ **ETL integration** - Categories copied to build directory in Stage 0

#### Category Consolidation
- ✅ **Byproduct consolidation** - `pulp` and `serum` → `byproduct`
- ✅ **Citrus hierarchy** - `part:fruit:peel:flavedo` and `part:fruit:peel:albedo`
- ✅ **Fungus hierarchy** - `part:fruiting_body:cap` and `part:fruiting_body:stipe`
- ✅ **Missing parents** - Added `part:cut` and `part:oil` parent parts

#### Validation Improvements
- ✅ **Dynamic validation** - `_validate_part_category_values` reads from categories.json
- ✅ **Error handling** - Proper error messages for missing/invalid categories
- ✅ **Consistency** - Both JSONL and JSON validators use same ontology

**Result**: Category system is now ontology-driven, self-validating, and UI-ready.

### ✅ Phase 1.6: Database Integration (COMPLETED)

**Date**: December 2024  
**Status**: ✅ COMPLETED - Categories fully integrated into database with UI query support

#### Database Integration Implementation
- ✅ **Stage F Integration** - Added categories table to SQLite schema
- ✅ **Category Loading** - Load categories.json into database during pack phase
- ✅ **Part-Category Linking** - Parts table references category IDs with foreign key constraints
- ✅ **UI Query Support** - Enabled category-based filtering and grouping

#### Implementation Details
1. **Categories table added to Stage F**:
   ```sql
   CREATE TABLE IF NOT EXISTS categories (
     id TEXT PRIMARY KEY,
     name TEXT NOT NULL,
     description TEXT,
     kind TEXT NOT NULL
   );
   ```

2. **Categories loaded during pack phase**:
   - ✅ Read `compiled/categories.json` in Stage F
   - ✅ Insert all 32 categories into database
   - ✅ Added foreign key constraint from parts to categories

3. **Part queries enabled**:
   - ✅ Enable `JOIN` queries between parts and categories
   - ✅ Support category-based filtering in UI
   - ✅ Add category metadata to part API responses

4. **Validation integration**:
   - ✅ Ensure all parts reference valid category IDs
   - ✅ Add referential integrity checks
   - ✅ Validate category-part kind consistency

#### Technical Fixes Applied
- **Transaction Timing** - Added proper `con.commit()` after categories insertion
- **Dependency Resolution** - Implemented topological sort for part parent-child relationships
- **Validator Paths** - Fixed validators to read from compiled directory
- **Data Consistency** - Fixed duplicate parts and naming conventions

**Result**: Categories are now fully integrated into the database with 32 categories, 66 parts with proper category references, and complete UI query support.

## Comprehensive Implementation Plan

**Status: ✅ READY FOR EXECUTION** - All issues identified, solutions designed, and implementation plan finalized.

### **Phase 1: Critical Schema & Data Fixes (Immediate - Week 1)**

#### 1.1 Fix Schema Violations
**Problem**: Current schemas don't match actual data usage
- `part.schema.json` allows `kind: "plant|animal|fungus|any"` but data uses `kind: "bird"` and `kind: "derived"`
- `transform.schema.json` missing `order` field used throughout transforms.json

**Solution**:
- Update `part.schema.json` to allow `kind: "plant|animal|fungus|derived"` and add `category` field
- Update `transform.schema.json` to include `order` field
- Change `kind: "bird"` → `kind: "animal"` for all egg parts (part:egg, part:egg:white, part:egg:yolk)
- Add `category: "egg"` to egg parts for specificity

**Justification**: Schemas should reflect actual usage. `bird` is not a biological kind but a taxonomic category. The `category` field provides the specificity needed for egg parts while keeping `kind` biological. This aligns with the ontology bible's approach to part classification.

#### 1.2 Fix Duplicate Parts
**Problem**: Multiple definitions of same parts causing validation failures
- `part:liver` (line 235) duplicates `part:organ:liver` (line 80)
- `part:egg_white` (line 37) duplicates `part:egg:white` (line 255)
- `part:egg_yolk` (line 45) duplicates `part:egg:yolk` (line 261)

**Solution**:
- Remove flat duplicates: `part:liver`, `part:egg_white`, `part:egg_yolk`
- Keep hierarchical versions: `part:organ:liver`, `part:egg:white`, `part:egg:yolk`
- Update all references to use hierarchical versions

**Justification**: Hierarchical naming is more consistent and allows for better organization. The flat versions are legacy and should be removed.

#### 1.3 Fix Parameter Mismatches
**Problem**: Inconsistent parameter names breaking family system
- `tf:strain` uses `target_TS_pct` but families.json references `strain_level`
- `tf:clarify?` in families.json but actual transform is `tf:clarify_butter`
- `lactobacillus` in derived_foods.jsonl but tf:ferment enum doesn't include it

**Solution**:
- Rename `target_TS_pct` → `strain_level` in transforms.json (more intuitive, widely used)
- Fix `tf:clarify?` → `tf:clarify_butter` in families.json
- Fix `lactobacillus` → `yogurt_thermo` in derived_foods.jsonl

**Justification**: `strain_level` is more intuitive than `target_TS_pct` (total solids percentage). It's used in 3 places vs 2, and better conveys yogurt consistency concept.

### **Phase 2: Transform Canonicalization (Week 1-2)**

#### 2.1 Merge Duplicate Transforms
**Problem**: Multiple transform definitions with conflicting parameters and orders
- 3 instances of `tf:smoke` (lines 127, 190, 746) with different params and orders (50, 40, 65)
- 2 instances of `tf:cure` (lines 106, 158) with different params and orders (40, 20)
- 2 instances of `tf:cook` (lines 17, 249) with different params and orders (90, 75)
- 2 instances of `tf:dry` (lines 210, 708) with different params and orders (45, 90)

**Solution**:
- Merge all `tf:smoke` instances into one comprehensive transform with all parameters
- Merge all `tf:cure` instances into one comprehensive transform with all parameters
- Merge all `tf:cook` instances into one comprehensive transform with all parameters
- Merge all `tf:dry` instances into one comprehensive transform with all parameters
- Use logical ordering: cure(20) → smoke(50) → cook(75) → age(80)

**Justification**: Single source of truth per transform ID. Multiple definitions cause confusion and validation failures. Logical ordering follows food processing sequence.

#### 2.2 Standardize Parameters
**Problem**: Inconsistent parameter naming across transforms and families
- Hierarchical names: `smoke.temp_C`, `age.time_d` vs flat names: `temp_C`, `time_d`
- Mixed parameter references in families vs transforms

**Solution**:
- Standardize to flat parameter names: `temp_C`, `time_d`, `salt_pct`
- Update all families.json references to use flat names
- Ensure consistent parameter types across all transforms

**Justification**: Flat names are simpler, reduce cognitive load, and make API cleaner. Hierarchical naming adds complexity without clear benefit.

### **Phase 3: Part Hierarchy & Product Anchoring (Week 2-3)**

#### 3.1 Fix Dairy Hierarchy
**Problem**: Incomplete dairy product hierarchy
- `part:butter` should be `part:cream` → `part:milk` (not direct to milk)
- Missing parent relationships for dairy products

**Solution**:
- Fix hierarchy: `part:butter` → `part:cream` → `part:milk`
- Add missing parent relationships:
  - `part:curd` → `part:milk`
  - `part:whey` → `part:milk`
  - `part:buttermilk` → `part:cream` (churned) and `part:milk` (cultured)

**Justification**: Preserves the cream step in butter production. Distinguishes between churned buttermilk (from cream) and cultured buttermilk (from milk).

#### 3.2 Fix Citrus Anatomy
**Problem**: Anatomically incorrect citrus part structure
- `part:peel`, `part:pith`, `part:flavedo` are separate parts
- Should be: `flavedo` and `pith` (albedo) are layers OF the peel

**Solution**:
- Restructure: `part:fruit:peel` → `part:fruit:peel:flavedo` + `part:fruit:peel:albedo`
- Add synonyms: `flavedo` = `zest`, `albedo` = `pith`
- Update all references to use new structure

**Justification**: Anatomically correct. `flavedo` (zest) and `albedo` (pith) are both layers of the peel, not separate parts.

#### 3.3 Implement Product-Part Anchoring
**Problem**: TPTs use substrate parts instead of product parts
- Butter TPT uses `part_id: "part:cream"` (substrate) instead of `part:butter` (product)
- Users search for "butter" but get no results due to substrate anchoring

**Solution**:
- **Split registry architecture**: `parts.core.json` (biological/anatomical) + `parts.derived.jsonl` (product parts)
- **Build step merges** into `build/parts.registry.json` (single authoritative registry)
- **Add missing derived parts** to `parts.derived.jsonl`:
  ```jsonl
  {"id":"part:butter","name":"butter","kind":"derived","category":"dairy","parent_id":"part:cream","notes":"Churned water-in-oil emulsion from cream"}
  {"id":"part:yogurt","name":"yogurt","kind":"derived","category":"dairy","parent_id":"part:fermented_milk","notes":"Fermented milk product"}
  {"id":"part:cheese","name":"cheese","kind":"derived","category":"dairy","parent_id":"part:milk","notes":"Coagulated milk product"}
  ```
- **Update TPTs** to use product parts: `part_id: "part:butter"` not `part:cream`
- **ETL2 compilation** reads from merged registry

**Justification**: Clean separation of concerns. Core parts stay biological, derived parts are processed. Product anchoring matches user mental model. Split registry provides clear ownership while maintaining single source of truth through merge step.

#### 3.4 Add Missing Parent Relationships
**Problem**: Incomplete part hierarchies
- Grain components missing parent relationships
- Animal parts missing parent relationships

**Solution**:
- Add parent relationships:
  - `part:bran` → `part:grain`
  - `part:germ` → `part:grain`
  - `part:endosperm` → `part:grain`
  - `part:marrow` → `part:bone`
  - `part:fat:subcutaneous` → `part:fat`

**Justification**: Complete hierarchies enable proper ancestry queries and logical organization.

### **Phase 4: Enhanced Validation & Metadata (Week 3-4)**

#### 4.1 Add Stage F Validators
**Problem**: Missing validation for critical issues
- No parameter validation in Stage F
- No enum compliance checking
- No part ancestry validation
- No cycle detection

**Solution**:
- Add SQL validators to Stage F:
  ```sql
  -- Parameter validation
  -- Enum violations check
  -- Part ancestry validation
  -- Cycle detection
  -- Cross-reference integrity
  ```
- Integrate into ETL2 pipeline

**Justification**: Catch issues early in compilation. Prevent data corruption and ensure consistency.

#### 4.2 Add Missing Metadata
**Problem**: Incomplete metadata for UI and functionality
- Missing family metadata for UI chips
- Missing diet/safety rules for flag evaluation
- Missing cuisine mappings for cultural context
- Missing comprehensive TPT examples

**Solution**:
- Add `family_meta.json` with labels, icons, colors
- Add `diet_safety_rules.jsonl` for flag evaluation
- Add `cuisine_map.jsonl` for cultural context
- Add comprehensive TPT examples for edge-case testing

**Justification**: Complete metadata enables full UI functionality and proper flag evaluation.

#### 4.3 Technical Implementation Details
**Problem**: Need specific code changes and data structures to implement the conceptual plan
- Missing concrete Stage F Python code changes
- Missing specific SQL validation queries
- Missing exact data structures and schemas
- Missing CI integration for validation

**Solution**: Implement comprehensive technical patch with three components:

**A. Stage F Patch (Python + SQL)**
- **Add `part_ancestors` table** with transitive closure population
- **Fix flag evaluation** to track all occurrences instead of "last wins"
- **Add TP backfill** for product-anchored TPTs
- **Add post-pack validation** with specific SQL queries

**B. Lint Pack (Stage F post-pack checks)**
- **Create `validate_sqlite.py`** script for CI integration
- **Add specific validation queries** for critical issues
- **Generate JSON reports** for validation results

**C. Data Deltas**
- **Add product parts** to `parts.json` with proper hierarchies
- **Add missing metadata files** with exact JSON structures
- **Add corrected TPT exemplars** with product anchoring
- **Update schemas** with missing fields

**Justification**: Provides concrete implementation details needed to execute the conceptual plan. Includes working code, exact data structures, and CI integration.

### **Phase 5: Cleanup & Polish (Week 4)**

#### 5.1 Fix Taxon Issues
**Problem**: Inconsistent taxonomic naming
- `gadoidea` vs `gadidae` for same fish family
- `lepus:europeaus` should be `lepus:europaeus`
- Mixed trailing colon usage in taxon paths

**Solution**:
- Standardize to `gadidae` (more current)
- Fix species misspelling: `europaeus`
- Standardize taxon path format: prefixes end with `:`, full IDs don't

**Justification**: Consistent naming prevents confusion and enables proper matching.

#### 5.2 Final Validation
**Problem**: Need to ensure all fixes work together
- ETL2 pipeline must pass all validations
- All references must resolve correctly
- UI must display correctly

**Solution**:
- Run full ETL2 pipeline with all validations
- Verify all cross-references resolve
- Test UI functionality
- Update documentation

**Justification**: Comprehensive testing ensures system works end-to-end.

## Implementation Details

### **Schema Updates**
```json
// part.schema.json additions
"kind": {
  "type": "string",
  "enum": ["plant", "animal", "fungus", "derived"]
},
"category": {
  "type": "string",
  "description": "Part category: organ, cut, fat, egg, grain, fruit, dairy, oil, etc."
}

// transform.schema.json additions
"order": {
  "type": "number",
  "description": "Processing order for transform sequence"
}
```

### **Transform Merging Strategy**
- Use most complete parameter set as base
- Merge all parameters from duplicate instances
- Use logical ordering based on food processing sequence
- Ensure parameter types are consistent

### **Product-Part Anchoring Architecture**
- **Core parts** (`parts.core.json`): Biological/anatomical + primary process parts (e.g., milk, cream, muscle, fruit)
- **Derived parts** (`parts.derived.jsonl`): Product parts (butter, yogurt, hard cheese, lard, ghee, oil:virgin/refined, fillet, fruit:peel:*)
- **Registry merge**: Stage 0/A merges these into `build/parts.registry.json` (the single authoritative parts table used by all later stages)
- **TPT anchoring**: Use product parts for derived foods (e.g., `part:butter`). Substrate queries use `part_ancestors` built from the merged registry

### **Validation Integration**
- Add Stage F SQL validators for parameter compliance
- Add enum validation for transform parameters
- Add part ancestry validation with cycle detection
- Add cross-reference integrity checks

## Detailed Technical Implementation

### **Stage F Patch (Python + SQL)**

#### A. DDL Additions
Add to `etl/mise/stages/stage_f/sqlite_pack.py` in the main DDL string:

```sql
-- Part closure (mirror of taxon_ancestors)
CREATE TABLE IF NOT EXISTS part_ancestors (
  descendant_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  ancestor_id   TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  depth INTEGER NOT NULL,
  PRIMARY KEY (descendant_id, ancestor_id)
);

-- Uniqueness for TPT identity within (taxon, part)
CREATE UNIQUE INDEX IF NOT EXISTS uq_tpt_identity
ON tpt_nodes(taxon_id, part_id, identity_hash);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_part_anc_desc_depth ON part_ancestors(descendant_id, depth);
CREATE INDEX IF NOT EXISTS idx_tpt_identity_tf ON tpt_identity_steps(tf_id);
```

#### B. Flag Evaluation Fix
Replace the `_build_identity_index` function to track all occurrences:

```python
def _build_identity_index(identity_steps: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """{ transform_id: [params_dict, ...] } preserve **all** occurrences per tf."""
    idx: Dict[str, List[Dict[str, Any]]] = {}
    for s in identity_steps or []:
        if isinstance(s, dict) and "id" in s:
            idx.setdefault(s["id"], []).append(s.get("params") or {})
    return idx
```

Update `_eval_condition` to check ANY occurrence:

```python
def _eval_condition(cond: Dict[str, Any], id_idx: Dict[str, List[Dict[str, Any]]], part_id: str) -> bool:
    # ... existing code ...
    if "param" in cond:
        p = cond["param"]
        if "." not in p:  # must be tf:id.param
            return False
        tf_id, param_path = p.split(".", 1)
        # ANY occurrence may satisfy the predicate
        occ = id_idx.get(tf_id, [])
        op = cond.get("op")
        cmpv = cond.get("value")
        for params in occ:
            val = _param_get(params, param_path)
            if op == "exists" and val is not None:
                return True
            if op == "eq" and val == cmpv:
                return True
            if op == "ne" and val != cmpv:
                return True
            try:
                if op in ("gt","gte","lt","lte"):
                    av, bv = _num(val), _num(cmpv)
                    if av is None or bv is None:
                        continue
                    if ((op=="gt" and av>bv) or (op=="gte" and av>=bv) or
                        (op=="lt" and av<bv) or (op=="lte" and av<=bv)):
                        return True
                if op == "in":
                    arr = cmpv if isinstance(cmpv, list) else [cmpv]
                    if val in arr:
                        return True
                if op == "not_in":
                    arr = cmpv if isinstance(cmpv, list) else [cmpv]
                    if val not in arr:
                        return True
            except Exception:
                continue
        return False
    return False
```

#### C. Part Ancestors Population
Add after parts are inserted:

```python
# 4) Populate part_ancestors (transitive closure)
cur.execute("DELETE FROM part_ancestors")
cur.execute(
    """
    INSERT OR REPLACE INTO part_ancestors(descendant_id, ancestor_id, depth)
    WITH RECURSIVE chain(descendant_id, ancestor_id, depth) AS (
      SELECT id, id, 0 FROM part_def
      UNION ALL
      SELECT chain.descendant_id, part_def.parent_id, chain.depth+1
      FROM chain JOIN part_def ON part_def.id = chain.ancestor_id
      WHERE part_def.parent_id IS NOT NULL
    )
    SELECT * FROM chain;
    """
)
# Depth sanity (warn >5)
cur.execute("SELECT COALESCE(MAX(depth),0) FROM part_ancestors")
if (cur.fetchone() or [0])[0] > 5:
    print("[WARN] part_ancestors depth exceeds 5—check for hierarchy smell")
```

#### D. TP Backfill for Product-Anchored TPTs
Add after TPT insertion:

```python
# Backfill TP nodes for any (taxon, part) used by TPTs but missing from tp_index
cur.execute(
  """
  SELECT DISTINCT t.taxon_id, t.part_id
  FROM tpt_nodes t
  LEFT JOIN taxon_part_nodes tp
    ON tp.taxon_id = t.taxon_id AND tp.part_id = t.part_id
  WHERE tp.id IS NULL
  """
)
for (tid, pid) in cur.fetchall():
    tp_id = f"{tid}:{pid}"
    default_name = f"{_last(tid)} {parts_index.get(pid, {}).get('name', _last(pid))}"
    slug = f"{_last(tid)}-{_last(pid)}"
    cur.execute(
        """
        INSERT OR REPLACE INTO taxon_part_nodes (id, taxon_id, part_id, name, display_name, slug)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (tp_id, tid, pid, default_name, default_name, slug)
    )
```

#### E. Post-Pack Validation
Add before closing connection:

```python
# --- Soft validation reports (stdout) ---
try:
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    # Derived parts must trace to a biological ancestor
    cur.execute(
      """
      WITH bio AS (
        SELECT id FROM part_def WHERE kind IN ('plant','animal','fungus')
      )
      SELECT p.id
      FROM part_def p
      LEFT JOIN part_ancestors a ON a.descendant_id = p.id
      LEFT JOIN bio b ON b.id = a.ancestor_id
      WHERE p.kind='derived'
      GROUP BY p.id
      HAVING MAX(CASE WHEN b.id IS NOT NULL THEN 1 ELSE 0 END)=0;
      """
    )
    rows = cur.fetchall()
    if rows:
        print("[ERROR] Derived parts lacking biological ancestry:", [r[0] for r in rows])

    # Unknown transform params (likely typos)
    cur.execute(
      """
      WITH keys AS (
        SELECT t.id tf_id, json_extract(k.value,'$.key') AS p
        FROM transform_def t, json_each(t.param_keys) k
      )
      SELECT s.tpt_id, s.tf_id, k2.key AS unknown_key
      FROM tpt_identity_steps s, json_each(s.params_json) k2
      LEFT JOIN keys ON keys.tf_id = s.tf_id AND keys.p = k2.key
      WHERE keys.p IS NULL;
      """
    )
    bad = cur.fetchall()
    if bad:
        print("[ERROR] Unknown transform param keys:", bad[:10], "… (truncated)" if len(bad)>10 else "")

    # Enum violations
    cur.execute(
      """
      WITH p AS (
        SELECT id tf_id, json_extract(k.value,'$.key') key,
               json_extract(k.value,'$.enum') enum_vals
        FROM transform_def, json_each(param_keys) k
        WHERE json_type(json_extract(k.value,'$.enum')) IS NOT NULL
      )
      SELECT s.tpt_id, s.tf_id, kv.value bad_value, p.key
      FROM tpt_identity_steps s, json_each(s.params_json) kv
      JOIN p ON p.tf_id = s.tf_id AND p.key = kv.key
      WHERE NOT EXISTS (
        SELECT 1 FROM json_each(p.enum_vals) e WHERE e.value = kv.value
      );
      """
    )
    ev = cur.fetchall()
    if ev:
        print("[ERROR] Enum violations:", ev[:10], "… (truncated)" if len(ev)>10 else "")
finally:
    con.close()
```

### **Lint Pack (Stage F post-pack checks)**

#### Create `etl/mise/stages/stage_f/validate_sqlite.py`:

```python
from __future__ import annotations
import json, sys
from pathlib import Path
import sqlite3
from mise.config import BuildConfig

CRITICAL = []
WARN = []

SQLS = {
    "derived_without_bio": {
        "sev": "critical",
        "sql": """
            WITH bio AS (
              SELECT id FROM part_def WHERE kind IN ('plant','animal','fungus')
            )
            SELECT p.id
            FROM part_def p
            LEFT JOIN part_ancestors a ON a.descendant_id = p.id
            LEFT JOIN bio b ON b.id = a.ancestor_id
            WHERE p.kind='derived'
            GROUP BY p.id
            HAVING MAX(CASE WHEN b.id IS NOT NULL THEN 1 ELSE 0 END)=0;
        """
    },
    "unknown_tf_params": {
        "sev": "critical",
        "sql": """
            WITH keys AS (
              SELECT t.id tf_id, json_extract(k.value,'$.key') AS p
              FROM transform_def t, json_each(t.param_keys) k
            )
            SELECT s.tpt_id, s.tf_id, k2.key AS unknown_key
            FROM tpt_identity_steps s, json_each(s.params_json) k2
            LEFT JOIN keys ON keys.tf_id = s.tf_id AND keys.p = k2.key
            WHERE keys.p IS NULL;
        """
    },
    "enum_violations": {
        "sev": "critical",
        "sql": """
            WITH p AS (
              SELECT id tf_id, json_extract(k.value,'$.key') key,
                     json_extract(k.value,'$.enum') enum_vals
              FROM transform_def, json_each(param_keys) k
              WHERE json_type(json_extract(k.value,'$.enum')) IS NOT NULL
            )
            SELECT s.tpt_id, s.tf_id, kv.value bad_value, p.key
            FROM tpt_identity_steps s, json_each(s.params_json) kv
            JOIN p ON p.tf_id = s.tf_id AND p.key = kv.key
            WHERE NOT EXISTS (
              SELECT 1 FROM json_each(p.enum_vals) e WHERE e.value = kv.value
            );
        """
    },
    "missing_tp_for_tpt": {
        "sev": "warn",
        "sql": """
            SELECT t.id, t.taxon_id, t.part_id
            FROM tpt_nodes t
            LEFT JOIN taxon_part_nodes tp
              ON tp.taxon_id=t.taxon_id AND tp.part_id=t.part_id
            WHERE tp.id IS NULL;
        """
    },
    "dup_identity_names": {
        "sev": "warn",
        "sql": """
            SELECT identity_hash, COUNT(*) c, GROUP_CONCAT(name, ' | ')
            FROM tpt_nodes
            GROUP BY identity_hash
            HAVING c>1;
        """
    }
}

def main():
    cfg = BuildConfig.from_env()
    db = cfg.db_path
    out = Path(cfg.build_root) / "report" / "verify_stage_f.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(db))
    cur = con.cursor()
    report = {}
    critical_found = False
    for key, spec in SQLS.items():
        cur.execute(spec["sql"])
        rows = cur.fetchall()
        report[key] = rows
        if rows and spec["sev"] == "critical":
            critical_found = True
    con.close()

    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if critical_found:
        print("Stage F validation failed — see", out)
        sys.exit(1)
    else:
        print("Stage F validation OK — see", out)

if __name__ == "__main__":
    main()
```

### **Data Deltas**

#### A. Product Parts for `parts.derived.jsonl`:

```jsonl
{"id":"part:butter","name":"butter","kind":"derived","category":"dairy","parent_id":"part:cream","notes":"Churned water-in-oil emulsion derived from cream"}
{"id":"part:ghee","name":"ghee","kind":"derived","category":"dairy","parent_id":"part:butter","notes":"Clarified butter (stage=ghee)"}
{"id":"part:cheese","name":"cheese","kind":"derived","category":"dairy","parent_id":"part:milk"}
{"id":"part:cheese:hard","name":"hard cheese","kind":"derived","category":"dairy","parent_id":"part:cheese"}
{"id":"part:cheese:soft","name":"soft/fresh cheese","kind":"derived","category":"dairy","parent_id":"part:cheese"}
{"id":"part:fermented_milk","name":"fermented milk","kind":"derived","category":"dairy","parent_id":"part:milk"}
{"id":"part:yogurt","name":"yogurt","kind":"derived","category":"dairy","parent_id":"part:fermented_milk"}
{"id":"part:oil:virgin","name":"virgin oil","kind":"derived","category":"oil","parent_id":"part:expressed_oil"}
{"id":"part:oil:refined","name":"refined oil","kind":"derived","category":"oil","parent_id":"part:expressed_oil"}
{"id":"part:fillet","name":"fillet","kind":"animal","category":"cut","parent_id":"part:muscle","notes":"Boneless longitudinal section (fish/meat)"}
{"id":"part:cut:leg","name":"leg (hind ham)","kind":"animal","category":"cut","parent_id":"part:muscle"}
{"id":"part:fruit:peel","name":"fruit peel","kind":"derived","category":"fruit","parent_id":"part:fruit","notes":"Peel has layers; see children"}
{"id":"part:fruit:peel:flavedo","name":"flavedo (zest)","kind":"derived","category":"fruit","parent_id":"part:fruit:peel"}
{"id":"part:fruit:peel:albedo","name":"albedo (pith)","kind":"derived","category":"fruit","parent_id":"part:fruit:peel"}
```

**Note:** Anatomical cuts like `part:fillet` and `part:cut:leg` use `kind:"animal"` + `category:"cut"` as they are anatomical segmentations, not process-derived products.

#### B. Schema Updates:

**`schemas/part.schema.json`**:
```json
{
  "kind": {"enum":["plant","animal","fungus","derived","any"]},
  "category": {"type":["string","null"]}
}
```

**`schemas/transform.schema.json`**:
```json
{
  "order": {"type":"integer"}
}
```

#### C. Metadata Files:

**`rules/family_meta.json`**:
```json
{
  "DAIRY_BUTTER":      {"label":"Butter & Clarified","icon":"🧈","color":"#f5c16c"},
  "DAIRY_YOGURT":      {"label":"Yogurt","icon":"🥣","color":"#b3d4ff"},
  "CHEESE_HARD":       {"label":"Hard Cheese","icon":"🧀","color":"#ffd166"},
  "OIL_VIRGIN":        {"label":"Virgin Oils","icon":"🫒","color":"#8bc34a"},
  "OIL_REFINED":       {"label":"Refined Oils","icon":"🛢️","color":"#9e9e9e"},
  "PORK_CURED_SMOKED": {"label":"Cured & Smoked Pork","icon":"🥓","color":"#f28b82"},
  "FISH_CURED_SMOKED": {"label":"Cured/Smoked Fish","icon":"🐟","color":"#80cbc4"}
}
```

**`rules/diet_safety_rules.jsonl`**:
```jsonl
{"when":{"param":"tf:cure.nitrite_ppm","op":"gt","value":0},"emit":"contains_nitrite","flag_type":"safety"}
{"when":{"has_transform":"tf:smoke"},"emit":"smoked","flag_type":"safety"}
{"when":{"allOf":[{"has_part":"part:milk"},{"noneOf":[{"has_transform":"tf:pasteurize"}]}]},"emit":"unpasteurized","flag_type":"safety"}
{"when":{"param":"tf:strain.strain_level","op":"gte","value":5},"emit":"greek_style","flag_type":"dietary"}
{"when":{"allOf":[{"has_transform":"tf:press"},{"noneOf":[{"has_transform":"tf:refine_oil"}]}]},"emit":"virgin_oil","flag_type":"dietary"}
{"when":{"allOf":[{"has_transform":"tf:press"},{"has_transform":"tf:age"},{"noneOf":[{"has_transform":"tf:stretch"}]}]},"emit":"cheese_hard_style","flag_type":"dietary"}
```

**Note:** Updated `target_TS_pct` to `strain_level` to match canonical parameter naming.

### **CI Integration**

Add to CI pipeline after `pnpm etl:run`:
```bash
python3 etl/mise/stages/stage_f/validate_sqlite.py
```

This comprehensive plan addresses all identified issues with clear solutions and justifications. The phased approach allows for systematic implementation while maintaining system stability.

### 🔧 Additional Validators Needed
1. **Taxonomic Naming Consistency** - Catch `gadoidea` vs `gadidae` conflicts
2. **Species Name Validation** - Catch misspellings like `lepus:europeaus`
3. **Transform ID Mismatches** - Catch `tf:clarify` vs `tf:clarify_butter` issues
4. **Missing Attribute Definitions** - Catch undefined parameters like `strain_level`
5. **Product Part Validation** - Ensure derived product parts have substrate ancestry
6. **Part Ancestry Consistency** - Validate part_ancestors table is complete and acyclic
7. **TPT Product Anchoring** - Validate TPTs are anchored to product parts where appropriate

### 📊 Automation Opportunities
1. **Report Parser** - Parse JSON validation reports for automated fixes
2. **Fix Generator** - Generate automated fixes for common error patterns
3. **CI/CD Integration** - Fail builds and provide fix suggestions
4. **Bulk Fix Scripts** - Automated scripts for systematic corrections

### 🔍 Research Needed
1. **Egg consumption patterns:** Do humans eat reptile eggs? Fish eggs (caviar/roe)?
2. **Other animal eggs:** Turtle eggs, crocodile eggs, etc.
3. **Cultural variations:** Different cultures may have different egg consumption patterns

### 🚀 Future Improvements
1. **Enhanced Validation** - Add more specific validators for remaining inconsistencies
2. **Automated Fixes** - Build tools to automatically fix common issues
3. **Hierarchy Traversal** - Implement hierarchy traversal in compilation process
4. **Standardization** - Standardize all part naming to hierarchical pattern

## Specific Metadata Items Requiring Fixes

### 1. Duplicate Parts (Critical - 3 items)
- **`part:liver`** (line 235) - Remove duplicate of `part:organ:liver`
- **`part:egg_white`** (line 37) - Remove legacy duplicate of `part:egg:white`  
- **`part:egg_yolk`** (line 45) - Remove legacy duplicate of `part:egg:yolk`

### 2. Missing Parent Relationships (Critical - 7 items)
- **`part:curd`** (line 278) - Add `parent_id: "part:milk"`
- **`part:whey`** (line 283) - Add `parent_id: "part:milk"`
- **`part:butter`** (line 288) - Add `parent_id: "part:milk"`
- **`part:buttermilk`** (line 293) - Add `parent_id: "part:milk"`
- **`part:bran`** (line 168) - Add `parent_id: "part:grain"`
- **`part:germ`** (line 173) - Add `parent_id: "part:grain"`
- **`part:endosperm`** (line 178) - Add `parent_id: "part:grain"`

### 3. Inconsistent Kind Values (Critical - 2 items)
- **`part:egg_white`** (line 37) - Change `kind: "animal"` to `kind: "bird"`
- **`part:egg_yolk`** (line 45) - Change `kind: "animal"` to `kind: "bird"`

### 4. Missing applies_to Arrays (Medium - 15 items)
Parts missing `applies_to: []` for consistency:
- `part:stem` (line 118)
- `part:flower` (line 123) 
- `part:root` (line 128)
- `part:tuber` (line 133)
- `part:bulb` (line 138)
- `part:rhizome` (line 143)
- `part:kernel` (line 148)
- `part:peel` (line 153)
- `part:pith` (line 158)
- `part:flavedo` (line 163)
- `part:bran` (line 168)
- `part:germ` (line 173)
- `part:endosperm` (line 178)
- `part:hull` (line 183)
- `part:skin` (line 215)

### 5. Duplicate Transform IDs (Critical - 4 items)
- **`tf:cure`** - Remove duplicate (lines 106-125 and 158-188)
- **`tf:smoke`** - Remove duplicate (lines 127-142 and 190-208)  
- **`tf:cook`** - Remove duplicate (lines 17-41 and 249-279)
- **`tf:dry`** - Remove duplicate (lines 210-231 and 708-727)

### 6. Inconsistent Transform Order Values (Medium - 6 items)
- **`tf:cure`** - Has conflicting orders 20 and 40
- **`tf:smoke`** - Has conflicting orders 40, 50, and 65
- **`tf:cook`** - Has conflicting orders 75 and 90
- **`tf:dry`** - Has conflicting orders 45 and 90
- **`tf:mill`** - Has conflicting orders 55 and 60
- **`tf:strain`** - Has conflicting orders 34 and 285

### 7. Missing Parent Relationships in Rules (Medium - 4 items)
- **`part:marrow`** - Should have `parent_id: "part:bone"`
- **`part:fat:subcutaneous`** - Should have `parent_id: "part:fat"`
- **`part:peel`** - Should have `parent_id: "part:fruit"` (for citrus)
- **`part:pith`** - Should have `parent_id: "part:fruit"` (for citrus)

### 8. Inconsistent Parameter Naming (Low - 3 items)
- **`tf:smoke`** - Uses both `style` and `mode` parameters
- **`tf:cure`** - Uses both `style` and `method` parameters  
- **`tf:dry`** - Uses both `temp_C` and `temperature` parameters

### 9. Missing Notes Fields (Low - 5 items)
Parts that could benefit from notes for clarity:
- `part:muscle` (line 31) - Add note about meat cuts
- `part:bone` (line 225) - Add note about marrow relationship
- `part:fat` (line 220) - Add note about fat types
- `part:roe` (line 240) - Add note about fish eggs
- `part:fillet` (line 245) - Add note about fish cuts

### 10. Rules Duplication (Medium - 2 items)
- **`part:muscle`** - Appears 8+ times in parts_applicability.jsonl
- **`part:milk`** - Appears 8+ times in parts_applicability.jsonl

### 11. Overly Specific Taxon Assignments (Critical - 12 items)
**Egg Parts - Too Specific:**
- **`part:egg_white`** (line 37) - Applied only to `tx:animalia:phasianidae:gallus:gallus_domesticus` (chicken only)
- **`part:egg_yolk`** (line 45) - Applied only to `tx:animalia:phasianidae:gallus:gallus_domesticus` (chicken only)

**Should be applied to broader bird groups:**
- **`part:egg`** - Correctly applied to `tx:animalia:chordata:aves` (all birds)
- **`part:egg:white`** - Correctly applied to `tx:animalia:chordata:aves` (all birds)  
- **`part:egg:yolk`** - Correctly applied to `tx:animalia:chordata:aves` (all birds)

**Missing Egg Assignments for Non-Bird Species:**
- **Reptile eggs** - No assignments for turtle, crocodile, or other reptile eggs
- **Fish eggs** - Only salmon roe assigned, missing caviar from sturgeon, paddlefish
- **Insect eggs** - No assignments for edible insect eggs

### 12. Inconsistent Taxon Path Formats (Medium - 15+ items)
**Missing trailing colons:**
- `tx:plantae:rosaceae:malus:` (line 1) - Has trailing colon
- `tx:plantae:rosaceae:pyrus:` (line 2) - Has trailing colon  
- `tx:plantae:rosaceae:prunus:` (line 3) - Has trailing colon
- `tx:plantae:musaceae:musa:` (line 13) - Has trailing colon
- `tx:plantae:rutaceae:citrus:` (line 21) - Has trailing colon
- `tx:plantae:vitaceae:vitis:` (line 22) - Has trailing colon
- `tx:plantae:poaceae:triticum:` (line 34) - Has trailing colon
- `tx:plantae:poaceae:oryza:` (line 35) - Has trailing colon
- `tx:plantae:alliaceae:allium:` (line 173) - Has trailing colon
- `tx:plantae:fabaceae:phaseolus:` (line 175) - Has trailing colon
- `tx:plantae:musaceae:musa:` (line 178) - Has trailing colon
- `tx:plantae:rutaceae:citrus:` (line 179) - Has trailing colon
- `tx:plantae:cucurbitaceae:cucurbita:` (line 180) - Has trailing colon

**Missing trailing colons:**
- `tx:plantae:brassicaceae:brassica:oleracea:var:capitata` (line 41) - Missing trailing colon
- `tx:plantae:brassicaceae:brassica:rapa:subsp:pekinensis` (line 42) - Missing trailing colon
- `tx:plantae:brassicaceae:brassica:oleracea:var:italica` (line 46) - Missing trailing colon
- `tx:plantae:brassicaceae:brassica:oleracea:var:botrytis` (line 47) - Missing trailing colon
- `tx:plantae:brassicaceae:brassica:rapa:subsp:rapa` (line 51) - Missing trailing colon
- `tx:plantae:brassicaceae:brassica:oleracea:var:capitata` (line 172) - Missing trailing colon
- `tx:plantae:brassicaceae:brassica:oleracea:var:italica` (line 171) - Missing trailing colon

### 13. Missing Parts in Animal Cuts (Medium - 3 items)
**Chicken cuts missing from parts.json:**
- **`part:cut:thigh`** - Defined in chicken.json but not in parts.json
- **`part:cut:wing`** - Defined in chicken.json but not in parts.json  
- **`part:cut:drumstick`** - Defined in chicken.json but not in parts.json

### 14. Inconsistent Family Assignments (Low - 5 items)
**Family allowlist inconsistencies:**
- **`part:cut:leg`** - Referenced in family_allowlist.jsonl but not defined in parts.json
- **`part:cut:shoulder`** - Referenced in family_allowlist.jsonl but not defined in parts.json
- **`part:meat`** - Referenced in family_expansions.jsonl but not defined in parts.json
- **`part:cut:fillet`** - Referenced in transform_applicability.jsonl but not defined in parts.json
- **`part:cut:brisket:flat`** - Referenced in transform_applicability.jsonl but not defined in parts.json

### 15. Duplicate Name Overrides (Low - 2 items)
- **Chicken Egg** - Appears twice in name_overrides.jsonl (lines 22 and 89)
- **Cow Milk** - Appears twice in name_overrides.jsonl (lines 13 and 86)

## ETL2 Validation Integration

**Status: ✅ IMPLEMENTED** - Ontology consistency validation has been successfully integrated into ETL2.

### Current Validation
- **Stage 0**: Taxa validation with `validate_taxa.py` (duplicate ID detection)
- **Stage A**: Transform canonicalization with built-in overrides
- **Stage E**: ID canonicalization and deduplication
- **Stage F**: SQLite packing with constraint validation

### ✅ Implemented Validators
1. **Parts validation** - Duplicate detection, schema compliance, hierarchy validation
2. **Transform validation** - Duplicate detection, parameter consistency
3. **Schema compliance** - Kind field validation against allowed values
4. **Hierarchy validation** - Parent-child relationship validation

### Implementation Details
- **Location**: `etl/mise/contracts/validators.py` - New validator functions added
- **Contracts**: Updated `stage_0/contract.yml` and `stage_a/contract.yml`
- **Execution**: Runs automatically with `pnpm etl:run --with-tests`
- **Reports**: Structured JSON reports in `etl/build/report/verify_stage_*.json`

### Validation Results
- **Schema Violations**: ✅ Caught `kind: "bird"` violations (should be `kind: "animal"`)
- **Duplicate Detection**: ✅ Ready to catch duplicate parts and transforms
- **Hierarchy Validation**: ✅ Ready to catch missing parent relationships
- **Parameter Consistency**: ✅ Ready to catch family/transform parameter mismatches

### Automation & Reporting
- **Structured Reports**: JSON format in `etl/build/report/verify_stage_*.json`
- **Error Format**: `file:path:[line]: error description with context`
- **CI/CD Integration**: Pipeline fails on validation errors
- **Fix Generation**: Easy to parse and generate automated fixes

### Quick Reference Commands
```bash
# Run full pipeline with validation
pnpm etl:run

# Run specific stage with validation
cd etl && python3 -m mise run A --with-tests

# Check validation reports
cat etl/build/report/verify_stage_0.json
cat etl/build/report/lint.json

# Clean and rebuild
pnpm etl:clean && pnpm etl:run
```

## Notes

- This document will be updated as more inconsistencies are discovered
- Focus on biological accuracy and cultural completeness
- Consider international/cultural variations in food consumption
- Maintain backward compatibility during transitions
- ETL2 validation should catch these issues before compilation

## External Analysis Validation

**Status: ✅ VALIDATED** - The external analysis has been verified against actual ontology files and is highly accurate.

### Validation Results:
- **Duplicate Parts**: 3 confirmed (part:liver, part:egg_white, part:egg_yolk)
- **Duplicate Transforms**: 4 confirmed (tf:cure, tf:smoke, tf:cook, tf:dry)  
- **Missing Parent Relationships**: 7 confirmed (dairy and grain hierarchies)
- **Inconsistent Kind Values**: 2 confirmed (egg parts)
- **Phantom Parts**: 5 confirmed (chicken cuts, family references)
- **Duplicate Name Overrides**: 2 confirmed (Chicken Egg, Cow Milk)
- **Parameter Mismatches**: 1 confirmed (strain_level vs target_TS_pct)

### Minor Clarifications:
- Taxon path trailing colons are intentional for prefix matching
- Some inconsistencies are more nuanced than initially reported

## Architectural Design Issues

### 1. Substrate vs Product Anchoring (Critical)

**Current Problem**: TPTs are substrate-anchored but users think in product terms
- **Butter TPT**: `part_id=part:cream` (substrate) - users search "butter" but get no results
- **Cheddar TPT**: `part_id=part:milk` (substrate) - cross-taxon grouping requires complex workarounds
- **Search/Filtering Misalignment**: Users filter by product categories ("butter", "yogurt", "hard cheese") but `part_id` points to substrates ("cream", "milk")

**Proposed Solution**: Product-part anchoring with part hierarchy
- **Butter TPT**: `part_id=part:butter` (product) with hierarchy `part:butter → part:cream → part:milk`
- **Cheddar TPT**: `part_id=part:cheese:hard` (product) with hierarchy `part:cheese:hard → part:cheese → part:milk`
- **Substrate Queries**: Use `part_ancestors` table to answer "is this dairy?" questions

**Benefits**:
- ✅ **Search & filtering match user intent** - filter by "butter" works natively
- ✅ **Cross-taxon grouping is trivial** - all butters (cow, goat, buffalo) share `part:butter`
- ✅ **Cleaner FTS synonyms** - "ghee/clarified butter" attach to `part:butter`
- ✅ **Better deduplication** - identity comparisons easier when "what it is" is first-class
- ✅ **Safety/diet flags still work** - flags are transform-driven, not part-driven

**Implementation Strategy**:
1. **Enrich `parts.json`** with product parts (`kind:"derived"`) and wire `parent_id` to substrates
2. **Add `part_ancestors` table** in Stage F (mirrors `taxon_ancestors` pattern)
3. **Emit product-anchored TPTs** during Stage E
4. **Keep substrate queries easy** via part ancestry closure

**Example Part Hierarchy**:
```
part:butter (derived) → parent part:cream → parent part:milk
part:yogurt (derived) → parent part:fermented_milk → parent part:milk  
part:cheese:hard (derived) → parent part:cheese → parent part:milk
part:oil:virgin (derived) → parent part:expressed_oil
```

**Migration Approach**: Incremental, low-risk
- Define product parts and wire parents
- Add `part_ancestors` table in Stage F
- Flip high-profile TPTs to product anchoring (Butter, Yogurt, Cheddar)
- Backfill TP rows for new product parts
- UI/FTS sanity check

**SQL for Part Ancestry**:
```sql
CREATE TABLE IF NOT EXISTS part_ancestors (
  descendant_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  ancestor_id   TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  depth INTEGER NOT NULL,
  PRIMARY KEY (descendant_id, ancestor_id)
);

-- Populate closure
WITH RECURSIVE chain(descendant_id, ancestor_id, depth) AS (
  SELECT id, id, 0 FROM part_def
  UNION ALL
  SELECT chain.descendant_id, part_def.parent_id, chain.depth+1
  FROM chain JOIN part_def ON part_def.id = chain.ancestor_id
  WHERE part_def.parent_id IS NOT NULL
)
INSERT OR REPLACE INTO part_ancestors(descendant_id, ancestor_id, depth)
SELECT * FROM chain;
```

**Query Examples**:
- "Show all dairy products": `WHERE EXISTS (SELECT 1 FROM part_ancestors a WHERE a.descendant_id = tpt.part_id AND a.ancestor_id = 'part:milk')`
- "Filter to products from fish muscle": `AND EXISTS (SELECT 1 FROM part_ancestors a WHERE a.descendant_id = tpt.part_id AND a.ancestor_id = 'part:muscle')`

**Trade-offs**:
- **Semantics of `has_part`**: "Cow has butter" is odd anatomically
  - *Pragmatic*: let `has_part` mean "yields/associated with" (keep schema)
  - *Purist*: add `produces_part` table for derived products (schema change)
- **Losing obvious substrate at `tpt_nodes.part_id`**: Mitigate with part ancestry closure

### 2. Missing Product Part Definitions (Critical)

**Current Issue**: No product parts defined for derived foods
- TPTs anchor on substrates (`part:milk`, `part:cream`) instead of products
- Users can't filter by product categories
- Cross-taxon grouping requires complex workarounds

**Required Product Parts**:
- `part:butter` (derived) → parent `part:cream`
- `part:yogurt` (derived) → parent `part:fermented_milk` → parent `part:milk`
- `part:cheese:hard` (derived) → parent `part:cheese` → parent `part:milk`
- `part:cheese:soft` (derived) → parent `part:cheese` → parent `part:milk`
- `part:oil:virgin` (derived) → parent `part:expressed_oil`
- `part:oil:refined` (derived) → parent `part:expressed_oil`
- `part:ghee` (derived) → parent `part:butter` → parent `part:cream`
- `part:lard` (derived) → parent `part:fat` → parent `part:muscle`
- `part:tofu` (derived) → parent `part:seed`
- `part:fillet` (derived) → parent `part:muscle`
- `part:cut:leg` (derived) → parent `part:muscle`

**Implementation Examples**:
```json
// parts.json additions
[
  {"id":"part:butter","name":"butter","kind":"derived","parent_id":"part:cream"},
  {"id":"part:cheese","name":"cheese","kind":"derived","parent_id":"part:milk"},
  {"id":"part:fermented_milk","name":"fermented milk","kind":"derived","parent_id":"part:milk"},
  {"id":"part:tofu","name":"tofu","kind":"derived","parent_id":"part:seed"},
  {"id":"part:fillet","name":"fillet","kind":"cut","parent_id":"part:muscle"},
  {"id":"part:cut:leg","name":"leg (hind ham)","kind":"cut","parent_id":"part:muscle"}
]
```

### 3. Missing Metadata and Validation Rules (Critical)

**Current Issues**:
- Missing family metadata for UI chips and grouping
- Incomplete diet/safety rules for flag evaluation
- Missing cuisine mappings for cultural context
- Inadequate name overrides for better display names
- Missing exemplar TPTs to test edge cases

**Required Metadata Additions**:

**Family Metadata** (`rules/family_meta.json`):
```json
{
  "DAIRY_BUTTER":       {"label":"Butter & Clarified","icon":"🧈","color":"#f5c16c"},
  "DAIRY_YOGURT":       {"label":"Yogurt","icon":"🥣","color":"#b3d4ff"},
  "CHEESE_HARD":        {"label":"Hard Cheese","icon":"🧀","color":"#ffd166"},
  "PORK_CURED_SMOKED":  {"label":"Cured & Smoked Pork","icon":"🥓","color":"#f28b82"},
  "SOY_TOFU":           {"label":"Tofu & Soy Curd","icon":"🫘","color":"#c1e1c1"},
  "OIL_VIRGIN":         {"label":"Virgin Oils","icon":"🫒","color":"#8bc34a"},
  "OIL_REFINED":        {"label":"Refined Oils","icon":"🛢️","color":"#9e9e9e"},
  "FISH_CURED_SMOKED":  {"label":"Cured/Smoked Fish","icon":"🐟","color":"#80cbc4"},
  "FISH_SALTED_DRY":    {"label":"Salted & Dried Fish","icon":"🐟","color":"#90a4ae"}
}
```

**Diet/Safety Rules** (`rules/diet_safety_rules.jsonl`):
```jsonl
{"when":{"param":{"p":"tf:cure.nitrite_ppm","op":"gt","value":0}},"emit":"contains_nitrite","flag_type":"safety"}
{"when":{"has_transform":"tf:smoke"},"emit":"smoked","flag_type":"safety"}
{"when":{"allOf":[{"has_part":"part:milk"},{"noneOf":[{"has_transform":"tf:pasteurize"}]}]},"emit":"unpasteurized","flag_type":"safety"}
{"when":{"param":{"p":"tf:strain.strain_level","op":"gte","value":5}},"emit":"greek_style","flag_type":"dietary"}
{"when":{"allOf":[{"has_transform":"tf:press"},{"noneOf":[{"has_transform":"tf:refine_oil"}]}]},"emit":"virgin_oil","flag_type":"dietary"}
{"when":{"allOf":[{"has_transform":"tf:press"},{"has_transform":"tf:age"},{"noneOf":[{"has_transform":"tf:stretch"}]}]},"emit":"cheese_hard_style","flag_type":"dietary"}
```

**Cuisine Mappings** (`rules/cuisine_map.jsonl`):
```jsonl
{"match":{"taxon_prefix":"tx:animalia:chordata:mammalia:artiodactyla:suidae:sus","parts":["part:cut:belly"]},"cuisines":["American","British","German"]}
{"match":{"taxon_prefix":"tx:animalia:chordata:actinopterygii:salmoniformes:salmo","parts":["part:fillet"]},"cuisines":["Nordic","Jewish"]}
{"match":{"taxon_prefix":"tx:plantae:fabaceae:glycine:max","parts":["part:seed","part:tofu"]},"cuisines":["Chinese","Japanese","Korean","Indian"]}
{"match":{"taxon_prefix":"tx:plantae:oleaceae:olea:europaea","parts":["part:expressed_oil"]},"cuisines":["Mediterranean","Middle Eastern"]}
```

**Name Overrides** (`rules/name_overrides.jsonl`):
```jsonl
{"taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus","part_id":"part:cut:belly","name":"pork belly","display_name":"Pork belly"}
{"taxon_id":"tx:plantae:oleaceae:olea:europaea","part_id":"part:expressed_oil","name":"olive oil","display_name":"Olive oil"}
```

**Taxon Part Synonyms** (`rules/taxon_part_synonyms.jsonl`):
```jsonl
{"taxon_id":"tx:plantae:oleaceae:olea:europaea","part_id":"part:expressed_oil","synonyms":["evoo","virgin olive oil","refined olive oil"]}
{"taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus","part_id":"part:cut:belly","synonyms":["streaky"]}
```

### 4. Transform Parameter Validation Issues (Critical)

**Current Issues**:
- Enum violations in transform parameters (e.g., `tf:ferment.starter` using `"lactobacillus"` instead of allowed values)
- Missing parameter validation in Stage F
- Inconsistent parameter naming across transforms
- Parameter drift unchecked - `tpt_identity_steps.params_json` keys not validated against `transform_def.param_keys`
- No unit semantics validation (temp_C vs temp_F, ppm vs %)

**Required Fixes**:
- **Yogurt starter enum**: Must be one of `["yogurt_thermo","yogurt_meso","kefir","culture_generic"]`
- **Parameter validation**: Add SQL checks in Stage F to catch enum violations
- **Parameter consistency**: Ensure parameter names match across families and transforms
- **Unit normalization**: Add unit validation and normalization (e.g., temp_F → temp_C)
- **Parameter drift detection**: Validate all param keys exist in transform definitions

**Stage F Validation Queries**:
```sql
-- Unknown param keys (typos)
WITH keys AS (
  SELECT t.tf_id, json_extract(k.value,'$.key') AS p
  FROM transform_def t, json_each(t.param_keys) k
)
SELECT s.tpt_id, s.tf_id, k2.key AS unknown_key
FROM tpt_identity_steps s,
     json_each(s.params_json) AS k2
LEFT JOIN keys ON keys.tf_id = s.tf_id AND keys.p = k2.key
WHERE keys.p IS NULL;

-- Steps referencing unknown transforms
SELECT DISTINCT tf_id FROM tpt_identity_steps
WHERE tf_id NOT IN (SELECT id FROM transform_def);

-- Enum violations check
WITH p AS (
  SELECT id tf_id, json_extract(k.value,'$.key') key,
         json_extract(k.value,'$.enum') enum_vals
  FROM transform_def, json_each(param_keys) k
  WHERE json_type(json_extract(k.value,'$.enum')) IS NOT NULL
)
SELECT s.tpt_id, s.tf_id, kv.value bad_value, p.key
FROM tpt_identity_steps s,
     json_each(s.params_json) kv
JOIN p ON p.tf_id = s.tf_id AND p.key = kv.key
WHERE NOT EXISTS (
  SELECT 1 FROM json_each(p.enum_vals) e WHERE e.value = kv.value
);

-- TPT with input part not present in has_part
SELECT t.id, t.taxon_id, t.part_id
FROM tpt_nodes t
LEFT JOIN has_part h ON h.taxon_id=t.taxon_id AND h.part_id=t.part_id
WHERE h.taxon_id IS NULL;
```

### 5. Additional Stage F Validation Issues (Critical)

**Current Issues**:
- **"Last transform wins" in flag evaluation** - `_build_identity_index` collapses repeated transforms by `id`, causing rules to miss earlier occurrences
- **Part aliases are global, not taxon-scoped** - Global aliases like "stone fruit" under `part:fruit` wrongly tag apples
- **Cuisine matching can't see transforms** - `tpt_cuisines` only matches `{taxon_prefix, parts}`, can't filter by transforms
- **Duplicate identities aren't surfaced** - `identity_hash` stored but not indexed/checked for duplicates
- **No cycle check in taxonomy** - `taxon_ancestors` assumes a DAG without cycle detection
- **Slug collisions only handled for taxa** - TP/TPT slugs aren't uniqueness-checked

**Required Fixes**:
- **Flag evaluation**: Let `when.param` accept `tf_id[n].param` or add `anyOf` across all occurrences
- **Part aliases**: Keep broad aliases in `taxon_part_synonyms.jsonl` (prefix-scoped), reserve `part_aliases` for universally true aliases
- **Cuisine matching**: Extend `cuisine_map.match` to allow `has_transform`, `param`, and optionally `family`
- **Duplicate detection**: Add `UNIQUE(taxon_id, part_id, identity_hash)` or at least an index + report
- **Cycle detection**: Add cycle detector prior to building taxonomy closure
- **Slug uniqueness**: Add deterministic de-dupe for TP/TPT slugs

**Stage F Improvements**:
```sql
-- Add unique constraint for TPT identity
CREATE UNIQUE INDEX uq_tpt_identity ON tpt_nodes(taxon_id, part_id, identity_hash);

-- Add index for parameter validation
CREATE INDEX idx_steps_param ON tpt_identity_steps(tf_id);

-- Cycle detection in taxonomy (SQLite-safe, before building taxon_ancestors)
WITH RECURSIVE climb(id, parent_id, path) AS (
  SELECT id, parent_id, '|'||id||'|' FROM taxon_def
  UNION ALL
  SELECT t.id, t.parent_id, path || t.id || '|'
  FROM taxon_def t
  JOIN climb c ON t.id = c.parent_id
  WHERE instr(c.path, '|' || t.id || '|') = 0
)
SELECT DISTINCT t.id
FROM taxon_def t
JOIN climb c ON t.parent_id = c.id
WHERE instr(c.path, '|' || t.id || '|') > 0;
```

### 6. Missing Exemplar TPTs (Medium)

**Current Issue**: Limited TPT examples to test edge cases and validate the system
- Missing examples for different transform combinations
- No examples for complex parameter scenarios
- Limited coverage of different food categories

**Required Exemplar TPTs**:
```jsonl
// Dairy products
{"id":"tpt:tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus:part:milk:unknown:greek-yogurt","taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus","part_id":"part:milk","family":"DAIRY_YOGURT","path":[{"id":"tf:ferment","params":{"starter":"yogurt_thermo"}},{"id":"tf:strain","params":{"strain_level":6}}],"identity":[{"id":"tf:ferment","params":{}},{"id":"tf:strain","params":{}}],"identity_hash":"","name":"Greek Yogurt","synonyms":["strained yogurt"],"notes":null}

{"id":"tpt:tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus:part:butter:unknown:ghee","taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus","part_id":"part:butter","family":"DAIRY_BUTTER","path":[{"id":"tf:clarify_butter","params":{"stage":"ghee"}}],"identity":[{"id":"tf:clarify_butter","params":{}}],"identity_hash":"","name":"Ghee","synonyms":["clarified butter"],"notes":null}

// Cured meats
{"id":"tpt:tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus:part:cut:belly:unknown:us-bacon","taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus","part_id":"part:cut:belly","family":"PORK_CURED_SMOKED","path":[{"id":"tf:cure","params":{"style":"dry","nitrite_ppm":120}},{"id":"tf:smoke","params":{"mode":"hot","time_h":4,"temp_C":80}}],"identity":[{"id":"tf:cure","params":{"nitrite_ppm":120,"style":"dry"}},{"id":"tf:smoke","params":{"mode":"hot"}}],"identity_hash":"","name":"American Bacon","synonyms":["streaky bacon (hot-smoked)"],"notes":null}

// Fish products
{"id":"tpt:tx:animalia:chordata:actinopterygii:salmoniformes:salmo:salar:part:fillet:unknown:cold-smoked-salmon","taxon_id":"tx:animalia:chordata:actinopterygii:salmoniformes:salmo:salar","part_id":"part:fillet","family":"FISH_CURED_SMOKED","path":[{"id":"tf:cure","params":{"style":"dry","nitrite_ppm":0}},{"id":"tf:smoke","params":{"mode":"cold","temp_C":22,"time_h":12}}],"identity":[{"id":"tf:cure","params":{"style":"dry","nitrite_ppm":0}},{"id":"tf:smoke","params":{"mode":"cold"}}],"identity_hash":"","name":"Cold-smoked Salmon","synonyms":["lox"],"notes":null}

// Plant products
{"id":"tpt:tx:plantae:rubiaceae:coffea:arabica:part:seed:unknown:light-roast","taxon_id":"tx:plantae:rubiaceae:coffea:arabica","part_id":"part:seed","family":"unknown","path":[{"id":"tf:roast","params":{"temp_C":210,"time_min":10}}],"identity":[{"id":"tf:roast","params":{}}],"identity_hash":"","name":"Light Roast Coffee","synonyms":["city roast"],"notes":null}

// Oils
{"id":"tpt:tx:plantae:arecaceae:cocos:nucifera:part:expressed_oil:unknown:virgin-coconut-oil","taxon_id":"tx:plantae:arecaceae:cocos:nucifera","part_id":"part:expressed_oil","family":"OIL_VIRGIN","path":[{"id":"tf:press","params":{}}],"identity":[{"id":"tf:press","params":{}}],"identity_hash":"","name":"Virgin Coconut Oil","synonyms":[],"notes":null}
```

**Edge-Case Exemplar TPTs** (comprehensive testing set):
```jsonl
// Greek yogurt - tests param validation and strain levels
{"id":"tpt:tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus:part:milk:unknown:greek-yogurt","taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus","part_id":"part:milk","family":"DAIRY_YOGURT","path":[{"id":"tf:ferment","params":{"starter":"yogurt_thermo"}},{"id":"tf:strain","params":{"strain_level":6}}],"identity":[{"id":"tf:ferment","params":{}},{"id":"tf:strain","params":{}}],"identity_hash":"","name":"Greek Yogurt","synonyms":["strained yogurt"],"notes":null}

// Prosciutto - tests long aging and zero nitrite
{"id":"tpt:tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus:part:muscle:unknown:prosciutto","taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus","part_id":"part:muscle","family":"PORK_CURED_SMOKED","path":[{"id":"tf:cure","params":{"salt_pct":3,"nitrite_ppm":0}},{"id":"tf:age","params":{"time_d":365}}],"identity":[{"id":"tf:cure","params":{"salt_pct":3,"nitrite_ppm":0}},{"id":"tf:age","params":{}}],"identity_hash":"","name":"Prosciutto crudo","synonyms":["prosciutto"],"notes":null}

// American bacon - tests multi-param allOf and safety flags
{"id":"tpt:tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus:part:cut:belly:unknown:us-bacon","taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus","part_id":"part:cut:belly","family":"PORK_CURED_SMOKED","path":[{"id":"tf:cure","params":{"nitrite_ppm":120}},{"id":"tf:smoke","params":{"mode":"hot","temp_C":80,"time_h":4}}],"identity":[{"id":"tf:cure","params":{"nitrite_ppm":120}},{"id":"tf:smoke","params":{"mode":"hot"}}],"identity_hash":"","name":"American Bacon","synonyms":["streaky bacon (hot-smoked)"],"notes":null}

// Cold-smoked salmon - tests mode validation and cuisine mapping
{"id":"tpt:tx:animalia:chordata:actinopterygii:salmoniformes:salmo:salar:part:fillet:unknown:cold-smoked-salmon","taxon_id":"tx:animalia:chordata:actinopterygii:salmoniformes:salmo:salar","part_id":"part:fillet","family":"FISH_CURED_SMOKED","path":[{"id":"tf:cure","params":{"style":"dry","nitrite_ppm":0}},{"id":"tf:smoke","params":{"mode":"cold","temp_C":22,"time_h":12}}],"identity":[{"id":"tf:cure","params":{"style":"dry","nitrite_ppm":0}},{"id":"tf:smoke","params":{"mode":"cold"}}],"identity_hash":"","name":"Cold-smoked Salmon","synonyms":["lox"],"notes":null}

// Salt cod (bacalhau) - tests high salt thresholds and alias cleanup
{"id":"tpt:tx:animalia:chordata:actinopterygii:gadiformes:gadus:morrhua:part:fillet:unknown:bacalhau","taxon_id":"tx:animalia:chordata:actinopterygii:gadiformes:gadus:morrhua","part_id":"part:fillet","family":"FISH_SALTED_DRY","path":[{"id":"tf:salt","params":{"salt_pct":20,"method":"dry"}},{"id":"tf:dry","params":{}}],"identity":[{"id":"tf:salt","params":{"salt_pct":20}},{"id":"tf:dry","params":{}}],"identity_hash":"","name":"Salt Cod (Bacalhau)","synonyms":["bacalhau","bacalao"],"notes":null}

// Ghee - tests derived parts and family alignment
{"id":"tpt:tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus:part:butter:unknown:ghee","taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus","part_id":"part:butter","family":"DAIRY_BUTTER","path":[{"id":"tf:clarify_butter","params":{"stage":"ghee"}}],"identity":[{"id":"tf:clarify_butter","params":{}}],"identity_hash":"","name":"Ghee","synonyms":["clarified butter"],"notes":null}

// Extra virgin olive oil - tests noneOf operator and cuisine mapping
{"id":"tpt:tx:plantae:oleaceae:olea:europaea:part:expressed_oil:unknown:evoo","taxon_id":"tx:plantae:oleaceae:olea:europaea","part_id":"part:expressed_oil","family":"OIL_VIRGIN","path":[{"id":"tf:press","params":{}}],"identity":[{"id":"tf:press","params":{}}],"identity_hash":"","name":"Extra Virgin Olive Oil","synonyms":["evoo","virgin olive oil"],"notes":null}

// Paneer - tests acid coagulation and derived parts
{"id":"tpt:tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus:part:milk:unknown:paneer","taxon_id":"tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus","part_id":"part:milk","family":"CHEESE_SOFT","path":[{"id":"tf:coagulate","params":{"agent":"acid"}},{"id":"tf:press","params":{}}],"identity":[{"id":"tf:coagulate","params":{}},{"id":"tf:press","params":{}}],"identity_hash":"","name":"Paneer","synonyms":[],"notes":"Fresh acid-set cheese"}

// Tofu - tests complex multi-step process and cuisine mapping
{"id":"tpt:tx:plantae:fabaceae:glycine:max:part:seed:unknown:tofu","taxon_id":"tx:plantae:fabaceae:glycine:max","part_id":"part:seed","family":"SOY_TOFU","path":[{"id":"tf:soak","params":{"time_h":8}},{"id":"tf:mill","params":{}},{"id":"tf:coagulate","params":{"agent":"nigari"}},{"id":"tf:press","params":{}}],"identity":[{"id":"tf:soak","params":{}},{"id":"tf:mill","params":{}},{"id":"tf:coagulate","params":{}},{"id":"tf:press","params":{}}],"identity_hash":"","name":"Tofu","synonyms":[],"notes":null}

// Coffee roast levels - tests numeric buckets and param validation
{"id":"tpt:tx:plantae:rubiaceae:coffea:arabica:part:seed:unknown:light-roast","taxon_id":"tx:plantae:rubiaceae:coffea:arabica","part_id":"part:seed","family":"unknown","path":[{"id":"tf:roast","params":{"agtron":75,"temp_C":210,"time_min":10}}],"identity":[{"id":"tf:roast","params":{}}],"identity_hash":"","name":"Light Roast Coffee","synonyms":["city roast"],"notes":null}
```

## Additional Inconsistencies Found

### **NEW CRITICAL ISSUES:**

#### 1. **Schema Violations (Critical - 2 items)**
- **Part Schema Violation**: `part.schema.json` allows `kind: "plant|animal|fungus|any"` but parts.json uses `kind: "bird"` and `kind: "derived"` which are not in the schema
- **Transform Schema Violation**: `transform.schema.json` is missing the `order` field which is used throughout transforms.json

**Resolution**: Update schemas to match actual usage. Use `kind: "animal"` + `category: "egg"` for egg parts instead of `kind: "bird"`. Add `derived` to kind enum and include `category` field.

#### 2. **Taxonomic Naming Inconsistencies (Critical - 2 items)**
- **Family Name Conflict**: Both `gadoidea` and `gadidae` are used for the same fish family
  - `gadoidea` appears in 8 places (name_overrides.jsonl, parts_applicability.jsonl, etc.)
  - `gadidae` appears in 12 places (taxa files, animals.jsonl, etc.)
- **Species Name Misspelling**: `lepus:europeaus` should be `lepus:europaeus` (missing 'e')
  - Appears in 3 files: name_overrides.jsonl, parts_applicability.jsonl, taxon_part_synonyms.jsonl

#### 3. **Transform Parameter Mismatches (Critical - 1 item)**
- **tf:strain Parameter Mismatch**: 
  - `tf:strain` uses parameter `target_TS_pct` (lines 287, 686 in transforms.json)
  - But `families.json` and `derived_foods.jsonl` reference `strain_level`
  - This breaks the family system for cultured dairy products

**Resolution**: Rename `target_TS_pct` → `strain_level` in transforms.json. `strain_level` is more intuitive and widely used.

#### 4. **Transform ID Mismatches (Critical - 1 item)**
- **tf:clarify vs tf:clarify_butter**:
  - `families.json` references `tf:clarify?` (line 260)
  - But actual transform is `tf:clarify_butter` (line 729 in transforms.json)
  - This breaks the BUTTER_DERIVATIVES family

**Resolution**: Fix `tf:clarify?` → `tf:clarify_butter` in families.json to match actual transform ID.

#### 5. **Missing Schema Fields (Medium - 1 item)**
- **Transform Schema Missing Order**: The `transform.schema.json` doesn't include the `order` field that's used throughout transforms.json, making validation impossible

### **NEW MEDIUM ISSUES:**

#### 6. **Missing Attribute Definitions (Medium - 1 item)**
- **strain_level Attribute**: Referenced in families and derived foods but not defined in attributes.json
- Should be added as `attr:strain_level` with appropriate enum values

#### 7. **Inconsistent Naming Patterns (Low - 1 item)**
- **Taxon Part Synonyms**: Some synonyms include processing states like "bacalhau (salted)" which should be in derived foods, not synonyms

**Total New Issues**: 8 additional inconsistencies beyond the external analysis

## Proposed Validation Rules

The following **lintable rules** have been validated and can be adopted for ETL2 integration. Each cluster can be turned into specific lint checks:

# Product-Part Anchoring Rules

1. **Product parts must have substrate ancestry.**
   * Every `part:*` with `kind: "derived"` must have a `parent_id` chain leading to a substrate (`kind: "plant|animal|fungus"`).
   * Rationale: Prevents orphaned product parts that can't be traced back to biological sources.

2. **TPT part_id should be product-anchored where appropriate.**
   * TPTs for derived foods should use product parts (`part:butter`, `part:yogurt`) not substrates (`part:cream`, `part:milk`).
   * Exception: TPTs for raw/primary foods can still use substrate parts.

3. **Part ancestry closure must be complete and acyclic.**
   * The `part_ancestors` table must include all descendant-ancestor relationships.
   * No cycles allowed in part hierarchy (A→B→A).

4. **Product parts must have corresponding TP rows.**
   * Every product part used in TPTs must have a corresponding `taxon_part_nodes` entry.
   * Enables proper FTS and search functionality.

5. **Part hierarchy depth limits.**
   * Reasonable depth limits (e.g., max 5 levels) to prevent infinite recursion.
   * Catch overly deep hierarchies that might indicate design issues.

## Proposed Validation Rules

The following **lintable rules** have been validated and can be adopted for ETL2 integration. Each cluster can be turned into specific lint checks:

# Transform rules (tf:*)

1. **Single source of truth per transform ID.**

   * One `id` ⇒ one schema (name, `identity`, params, and `order`).
   * Rationale: `tf:cure`, `tf:smoke`, `tf:cook`, `tf:dry`, `tf:mill` appear **multiple times** with different param sets and orders.
2. **Canonical param names & shapes.**

   * Choose one of `style|mode|method` (don’t mix).
   * Numeric vs enum must not conflict (e.g., `mode=cold|hot` vs `temp_C` buckets); if you keep numeric, derive labels downstream—not as parallel params.
3. **Order is stable and unique.**

   * Each transform gets a single `order` value; no duplicates across variants of the same unit op.
4. **Identity is defined centrally.**

   * Maintain a single allowlist of identity-bearing transforms. The transform JSON must match that list. (Today `pasteurize=false` while two versions of `cook=true` disagree with families/buckets logic.)
5. **Param units required and standardized.**

   * Enforce units for every numeric param (`% m/m`, `time_min`, `temp_C`, etc.). No free-text (`"00"` for milling is a *grade*, not a unit).
6. **Families and buckets must reference real params.**

   * Every `families.json` `identity_params` and `param_buckets.json` key must exist in the canonical transform spec.
   * Examples out-of-sync now: `tf:strain` has `target_TS_pct`, but families use `strain_level`; `tf:smoke` uses `mode` in some entries while bucket file uses `smoke.temp_C`.

# Part rules (part:*)

7. **One ID, one place.**

   * Define every `part:*` exactly once in `parts.json`. Other files (e.g., `animal_cuts/*.json`) may **reference** parts but never introduce new IDs or nested “children” trees.
   * Today: `part:cut:brisket:flat/point`, `part:cut:thigh/wing/drumstick` are defined outside `parts.json`.
8. **Hierarchy is explicit and acyclic.**

   * If a part is a child, set `parent_id` and ensure the parent exists. No drift between `parent_id` and “children” arrays elsewhere.
9. **`kind` vocabulary is closed.**

   * Allowed: `plant | animal | fungus | derived` (or whatever you pick)—but keep it consistent with the JSON Schema.
   * Today we see `bird` and `derived` used while schema allows only `plant|animal|fungus|any`. Align the set or add a new `category` field.
10. **No parallel IDs for the same concept.**

* Unify duplicates like `part:organ:liver` vs `part:liver`, and `part:egg_white` vs `part:egg:white`. Prefer the hierarchical form.

11. **“Process parts” are marked as derived.**

* Items like `cream`, `curd`, `whey`, `butter`, `expressed_oil/juice` are *derived*, not anatomical. Mark them with `kind: "derived"` (or dedicate `category`), not `animal|plant`.

# Taxon prefix & matching rules (tx:*)

12. **Prefix grammar is explicit.**

* End a *prefix* with `:`; a full ID has **no** trailing colon. Every matcher must declare whether it expects exact or prefix semantics.
* Today: mixed use like `tx:fungi:` vs `tx:fungi` and inconsistent trailing `:` in many rows.

13. **Taxonomy naming is current and consistent.**

* Families like `Alliaceae` vs `Amaryllidaceae` should not both appear. Lock the backbone and lint against outdated ranks.

# Applicability vs implied parts vs allowlists

14. **Separation of concerns.**

* `parts_applicability` = what parts are *allowed* for a taxon.
* `implied_parts` = parts to *auto-attach* by default.
* Enforce `implied ⊆ applicability`. Fail the build if violated.

15. **No phantom parts.**

* Any part referenced in `applicability`, `implied_parts`, or `family_allowlist` must exist in `parts.json`.
* Today: references to `part:meat`, `part:cut:fillet`, `part:cut:leg`, `part:cut:shoulder` don’t match canonical part IDs (`part:muscle`, `part:fillet`, etc.).

16. **No duplicated applicability rows.**

* De-duplicate repeated mappings (e.g., `part:muscle` → many taxa repeated across files). Prefer **prefix grouping** with explicit exceptions in `exclude`.

# Names, aliases, and synonyms

17. **Display name vs alias vs synonym are distinct.**

* `display_name` is canonical text for UI.
* `aliases` belong to the *part* (generic, e.g., `florets` for `part:flower`).
* `synonyms` belong to a specific `(taxon_id, part_id)`—but must not encode transforms/processing (“smoked salmon”, “bacalhau”) that change identity. Those belong in **derived foods**.

18. **No marketing or attribute claims in synonyms.**

* E.g., “free range eggs”, “raw milk” are attributes/flags, not synonyms. Route that signal to attributes or transforms present/absent.

19. **No parentheses or qualifiers inside synonyms.**

* Keep raw strings; qualifications like “(salted)” break search semantics.

20. **One `(taxon_id, part_id)` ⇒ one `name_overrides` row.**

* Duplicate rows must merge, and collision rules defined (last-wins is not enough).

# Families (product families / naming)

21. **Families only reference canonical transforms/params.**

* Every `identity_transforms` and `identity_params` must exist in `transforms.json`. Optional `?` suffix is allowed at *family* layer but must resolve to a real transform ID.
* Today: family uses `tf:clarify?` while the transform is `tf:clarify_butter`.

22. **Buckets are reusable by key, not duplicated.**

* `param_buckets.json` is the single registry. `families.json` may *reference* bucket IDs, not duplicate cutoffs.

23. **Allowlist keys must exist.**

* `family_allowlist` parts must be valid IDs (e.g., `part:fillet`, not `part:cut:fillet` unless that part exists). Enforce at build.

# Derived foods (tpt:*)

24. **Derived foods must be composable and valid.**

* Every path step references a real transform and valid params; `(taxon_id, part_id)` must pass applicability; names follow naming rules; synonyms must not include transform states already encoded by the path.

25. **IDs encode (taxon, part, identity path) minimally and stably.**

* Set a canonical sort for transforms in the ID to avoid ID churn when authors reorder JSON arrays.

# Attributes

26. **Transform params ↔ attributes are mapped deliberately.**

* If a transform param is used as an identity attribute (e.g., `lean_pct`, `fat_pct`, `salt_pct`), register it once in `attributes.json` with `role: "identity_param"` and reference that *attribute id* from the transform param (or vice versa) to keep names consistent.

27. **Attribute roles are non-overlapping.**

* `identity_param` vs `facet` vs `covariate` vs `taxon_refinement` are mutually exclusive per attribute.

# JSON Schemas & validation

28. **Schemas are the contract—keep them in sync.**

* Either update the schemas to include what you actually use (e.g., `kind: "derived"`) or refactor data to fit the schema. Enforce CI validation for every JSON/JSONL row.

29. **Cross-file referential integrity.**

* CI should fail if any file references unknown ids (part, transform, taxon), unknown params, unknown bucket keys, or non-canonical taxon prefixes.

30. **Prefix matching is explicit in schema.**

* Add a `match_type: "exact" | "prefix"` (or infer by trailing colon and lint it). Today it’s ambiguous and inconsistent.

# Naming, casing, and style

31. **ID grammar is frozen and linted.**

* `tf:[a-z0-9_]+`, `part:(segment:)+`, `tx:(segment:)+`, with segments `[a-z0-9_]+`. No accidental dashes or stray capitals.
* Trailing underscore or empty segments (`...:thunnus:`) are invalid unless intentionally “open prefix.”

32. **Title case for `display_name`, sentence case for `notes`, lower_snake for IDs.**
33. **No duplicate capitalization variants.**

* “EVOO” is allowed as an alias, but “Extra Virgin Olive Oil” is the display name; pick one case policy for acronyms.

# Data hygiene (examples of what to catch later, not to fix now)

* Misspellings: e.g., `lepus:europeaus` (should be `europaeus`), family/rank swaps (`gadoidea` vs `gadidae`).
* Phantom IDs: `part:meat`, `part:cut:leg`, `part:cut:shoulder`.
* Transform collisions: multiple `tf:smoke`/`tf:cure` with incompatible params and orders.
* Synonyms that encode transforms (“smoked salmon”, “bacalhau”), attributes (“raw milk”), or marketing (“free range eggs”).
* Mixed taxonomy backbones (`Alliaceae` vs `Amaryllidaceae`).
* Inconsistent trailing colons in taxon prefixes.

---
