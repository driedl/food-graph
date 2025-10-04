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
- `part:egg` has `kind: "bird"` ✅ **Correct**
- `part:egg_white` has `kind: "animal"` ❌ **Should be "bird"**
- `part:egg_yolk` has `kind: "animal"` ❌ **Should be "bird"**

**Note:** Need to research if reptiles/other animals have consumable eggs. If so, we may need:
- `part:egg` with `kind: "animal"` (general)
- `part:egg:bird` with `kind: "bird"` and `parent_id: "part:egg"`
- `part:egg:reptile` with `kind: "reptile"` and `parent_id: "part:egg"`

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
- `bird` - bird-specific parts
- `reptile` - reptile-specific parts
- `mammal` - mammal-specific parts
- `plant` - general plant parts
- `fungus` - fungus-specific parts
- `derived` - processed/derived products

### 3. Hierarchy Rules
- Parent parts should have broader applicability
- Child parts inherit parent applicability
- Only apply parent parts to taxa, not children
- Use `parent_id` to establish relationships

### 4. Egg Taxonomy Considerations

**Research needed:** Do humans consume eggs from non-bird species?

If yes, consider this hierarchy:
```
part:egg (kind: "animal", applies_to: [all egg-laying animals])
├── part:egg:bird (kind: "bird", parent_id: "part:egg")
├── part:egg:reptile (kind: "reptile", parent_id: "part:egg")
└── part:egg:fish (kind: "fish", parent_id: "part:egg")
    ├── part:egg:fish:caviar (kind: "fish", parent_id: "part:egg:fish")
    └── part:egg:fish:roe (kind: "fish", parent_id: "part:egg:fish")
```

## Action Items

### ✅ Completed
1. **ETL2 Validation Integration** - Implemented comprehensive validation system
2. **Schema Compliance Validation** - Catches kind field violations
3. **Duplicate Detection** - Ready to catch duplicate parts and transforms
4. **Hierarchy Validation** - Ready to catch missing parent relationships
5. **Parameter Consistency** - Ready to catch family/transform mismatches

### 🔥 Critical Fixes (Immediate)
1. **Fix Schema Violations** - Change `kind: "bird"` to `kind: "animal"` for egg parts
2. **Remove Duplicate Parts** - `part:liver`, `part:egg_white`, `part:egg_yolk`
3. **Fix Kind Values** - Update remaining egg parts to use correct kind values
4. **Add Parent Relationships** - Dairy products and grain components

### 🔧 Additional Validators Needed
1. **Taxonomic Naming Consistency** - Catch `gadoidea` vs `gadidae` conflicts
2. **Species Name Validation** - Catch misspellings like `lepus:europeaus`
3. **Transform ID Mismatches** - Catch `tf:clarify` vs `tf:clarify_butter` issues
4. **Missing Attribute Definitions** - Catch undefined parameters like `strain_level`

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
- **Location**: `etl2/mise/contracts/validators.py` - New validator functions added
- **Contracts**: Updated `stage_0/contract.yml` and `stage_a/contract.yml`
- **Execution**: Runs automatically with `pnpm etl2:run --with-tests`
- **Reports**: Structured JSON reports in `etl2/build/report/verify_stage_*.json`

### Validation Results
- **Schema Violations**: ✅ Caught `kind: "bird"` violations (should be `kind: "animal"`)
- **Duplicate Detection**: ✅ Ready to catch duplicate parts and transforms
- **Hierarchy Validation**: ✅ Ready to catch missing parent relationships
- **Parameter Consistency**: ✅ Ready to catch family/transform parameter mismatches

### Automation & Reporting
- **Structured Reports**: JSON format in `etl2/build/report/verify_stage_*.json`
- **Error Format**: `file:path:[line]: error description with context`
- **CI/CD Integration**: Pipeline fails on validation errors
- **Fix Generation**: Easy to parse and generate automated fixes

### Quick Reference Commands
```bash
# Run full pipeline with validation
pnpm etl2:run

# Run specific stage with validation
cd etl2 && python3 -m mise run A --with-tests

# Check validation reports
cat etl2/build/report/verify_stage_0.json
cat etl2/build/report/lint.json

# Clean and rebuild
pnpm etl2:clean && pnpm etl2:run
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

## Additional Inconsistencies Found

### **NEW CRITICAL ISSUES:**

#### 1. **Schema Violations (Critical - 2 items)**
- **Part Schema Violation**: `part.schema.json` allows `kind: "plant|animal|fungus|any"` but parts.json uses `kind: "bird"` and `kind: "derived"` which are not in the schema
- **Transform Schema Violation**: `transform.schema.json` is missing the `order` field which is used throughout transforms.json

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

#### 4. **Transform ID Mismatches (Critical - 1 item)**
- **tf:clarify vs tf:clarify_butter**:
  - `families.json` references `tf:clarify?` (line 260)
  - But actual transform is `tf:clarify_butter` (line 729 in transforms.json)
  - This breaks the BUTTER_DERIVATIVES family

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

