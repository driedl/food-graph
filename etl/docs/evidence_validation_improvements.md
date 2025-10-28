# Evidence Validation Improvements

## Summary

This document describes the comprehensive fixes implemented to improve evidence mapping quality and prevent invalid parameter mappings.

## Problem

The evidence mapping system was accepting invalid mappings:

1. **Frankfurters being mapped when they should be skipped** - Multi-ingredient processed products (beef + pork fat + spices + binders) were being assigned to single taxon
2. **LLM inventing invalid enum values** - e.g., `"style": "nitrite_cure"` instead of valid values `"dry"` or `"wet"`
3. **No validation rejecting bad mappings** - Invalid parameters passed through to database
4. **Semantically wrong transforms** - e.g., `tf:mill` (grain processing) used for meat emulsification

## Solution Implemented

### Part 1: Schema Validation (✅ Completed)

**File:** `etl/evidence/lib/schema_validator.py`

Created a strict validation module that:
- Validates part IDs exist in ontology
- Validates transform IDs exist in ontology
- **Validates parameter names** are defined for each transform
- **Validates enum values** match schema exactly
- **Validates parameter types** (number vs string)

**Integration:** `etl/evidence/evidence_mapper.py`
- Validation runs before TPT ID generation
- Invalid mappings are rejected with `disposition='rejected'`
- Validation errors are logged for debugging
- Builds ontology indices on initialization for fast lookups

### Part 2: Enhanced Tier 1 Prompt (✅ Completed)

**File:** `etl/evidence/lib/optimized_prompts.py` - `get_optimized_taxon_system_prompt()`

**Added explicit skip categories with examples:**

1. **Processed Meat Products**: Frankfurters, hot dogs, sausages, deli meats
2. **Condiments & Sauces**: Ketchup, mayonnaise, hummus, pesto
3. **Baked Goods**: Bread, cookies, cake (unless simple single-grain)
4. **Prepared Meals**: Pizza, sandwiches, stir-fry, casseroles
5. **Non-Biological**: Salt, minerals, water

**Key additions:**
- Explicit "ALWAYS SKIP THESE CATEGORIES" section
- ✅/❌ visual examples showing accept vs skip
- Specific frankfurter example: `"Frankfurter, beef" → disposition: "skip"`
- Reasoning for each category (multi-species blend, etc.)

### Part 3: Enhanced Tier 2 Prompt (✅ Completed)

**File:** `etl/evidence/lib/optimized_prompts.py` - `get_optimized_tpt_system_prompt()`

**Added complete parameter schemas with enum values:**

```
tf:cure (Curing - meat preservation):
  - style: ENUM["dry", "wet"] (REQUIRED - these are the ONLY valid values)
  - nitrite_ppm: number (optional)
  - salt_pct: number (optional)
  - sugar_pct: number (optional)
  - time_d: number (optional)
  CRITICAL: Do NOT invent values like "nitrite_cure" - use ONLY "dry" or "wet"
  Example: {"id": "tf:cure", "params": {"style": "wet", "nitrite_ppm": 120}}
```

**Added for all common transforms:**
- `tf:cook` - with all 10 method enum values
- `tf:mill` - with applicability note (ONLY for grains)
- `tf:cure` - with explicit warning about valid values
- `tf:dry`, `tf:brine`, `tf:trim`, `tf:standardize_fat`, `tf:roast`, `tf:enrich`
- `tf:pasteurize`, `tf:homogenize` - marked as non-identity

**Key additions:**
- Full enum value lists for each parameter
- Required vs optional parameter marking
- Transform applicability warnings (tf:mill for grains only)
- "CRITICAL VALIDATION RULES" section
- Examples for each transform

## Testing

Created and ran validation tests:

### Test 1: Frankfurter (Invalid Parameters)
```python
transforms: [
  {'id': 'tf:mill', 'params': {'target': 'fine_emulsion'}},  # Invalid enum
  {'id': 'tf:cure', 'params': {'style': 'nitrite_cure'}}    # Invalid enum
]
```
**Result:** ✅ Correctly rejected with errors:
- `Transform 1 (tf:mill): param 'target': invalid value 'fine_emulsion'. Must be one of: ['wholemeal', 'white', 'semolina', 'meal', 'flour']`
- `Transform 2 (tf:cure): param 'style': invalid value 'nitrite_cure'. Must be one of: ['dry', 'wet']`

### Test 2: Milk (Valid Parameters)
```python
transforms: [
  {'id': 'tf:pasteurize', 'params': {'regime': 'HTST'}},      # Valid
  {'id': 'tf:standardize_fat', 'params': {'fat_pct': 2.0}}   # Valid
]
```
**Result:** ✅ Correctly accepted

## Expected Impact

### Before Fix
```json
{
  "food_name": "Frankfurter, beef, unheated",
  "disposition": "mapped",
  "transforms": [{"id": "tf:cure", "params": {"style": "nitrite_cure"}}],
  "tpt_id": "tx:a:bos:taurus|part:muscle|abc123"
}
```

### After Fix (Tier 1)
```json
{
  "food_name": "Frankfurter, beef, unheated",
  "disposition": "skipped",
  "reason": "Multi-ingredient processed meat product (beef + pork fat + spices + binders)"
}
```

### After Fix (Tier 2 - if it got through)
```json
{
  "food_name": "Some food",
  "disposition": "rejected",
  "confidence": 0.0,
  "reason": "Schema validation failed: Transform 0 (tf:cure): param 'style': invalid value 'nitrite_cure'. Must be one of: ['dry', 'wet']"
}
```

## Files Modified

1. **New:** `etl/evidence/lib/schema_validator.py` - Validation logic
2. **Modified:** `etl/evidence/evidence_mapper.py` - Integration of validation
3. **Modified:** `etl/evidence/lib/optimized_prompts.py` - Enhanced prompts
4. **Related:** `etl/evidence/tpt_id_utils.py` - Fixed hash generation (separate task)

## Related Documentation

- **Code Unification**: Transform parameter utilities moved to `etl/lib/transform_utils.py`
- **TPT ID Fix**: Fixed path resolution and identity parameter filtering

## Next Steps

1. Delete existing `data/evidence/fdc-foundation/evidence_mappings.jsonl`
2. Re-run evidence mapping: `pnpm evidence:map --limit 100`
3. Verify:
   - Frankfurters are now skipped at Tier 1
   - Any bad parameters that slip through are rejected at validation
   - TPT IDs now have proper hashes instead of `|raw`

## Metrics to Track

After regeneration, check:
- Number of `disposition: "skipped"` (should increase)
- Number of `disposition: "rejected"` (should be minimal with better prompts)
- Number of `disposition: "mapped"` with valid params (should be majority)
- No mappings with invalid enum values in database

---

**Implementation Date:** October 26, 2025
**Status:** ✅ Complete and Tested

