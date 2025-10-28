# Tier 3 Validation Remediation - Implementation Complete

## What Was Implemented

### 1. Updated Tier 2 Prompts (optimized_prompts.py)
Added explicit **bucketing guidance** to fight drift:

**tf:ferment:**
- Use `'culture_generic'` for ALL cheese, sauerkraut, kimchi
- Use `'yogurt_thermo'` / `'yogurt_meso'` ONLY for actual yogurt
- DO NOT invent values like `'lactic_cultures'`, `'thermophilic lactic cultures'`

**tf:enrich:**
- Use `'std_enriched'` for common fortifications (milk+A/D, flour+B/Fe)
- DO NOT try to specify which vitamins/minerals
- Foods bucket by enrichment LEVEL, not specific vitamins

**tf:coagulate:**
- Use `'milk'` for whole milk, skim milk, 2% milk (fat handled by `tf:standardize_fat`)
- DO NOT specify fat content in substrate (e.g., NO `'whole_milk'`, `'skim_milk'`)

### 2. Added Tier 3 Remediation Method (tier3_curator.py)
New method: `remediate_validation_errors()`

**Strategy:**
1. **MAP** (90% of cases) - Map invalid values to existing broad groups
2. **EXPAND** (10% of cases) - Propose ontology expansion (high bar)
3. **REJECT** (<1% of cases) - Fundamentally wrong

**Decision Framework:**
- Defaults to BROADER groupings (fights drift)
- Expansion requires: nutritional distinction + multiple foods + clear benefit
- Uses LLM with bucketing philosophy prompts

### 3. Enhanced Schema Validator (schema_validator.py)
Added structured `ValidationError` objects with:
- `transform_index`, `transform_id`, `error_type`
- `param_name`, `attempted_value`, `valid_values`
- Full schema constraint for context

Returns `ValidationResult` instead of just `(bool, List[str])`

### 4. Updated Evidence Mapper (evidence_mapper.py)
Modified validation flow:
```
Tier 2 → [Validate] → if valid: Save
                    → if invalid: Tier 3 Remediation → if fixed: Save
                                                     → if unfixable: Reject
```

## How It Works

**Before (rejected 13/127 = 10.2%):**
```
Tier 2 creates TPT → Validation fails → REJECT immediately
```

**After (expected <2% rejection):**
```
Tier 2 creates TPT → Validation fails → Pass to Tier 3
                                          ↓
                                       Tier 3 LLM analyzes
                                          ↓
                                       ├─ MAP: 'lactic_cultures' → 'culture_generic'
                                       ├─ MAP: {'vitamin_A': 'added'} → 'std_enriched'
                                       ├─ MAP: 'whole_milk' → 'milk'
                                       └─ SAVE with corrected TPT
```

## Expected Remediation of Current Rejections

### 7 ferment errors → All map to 'culture_generic'
- `'lactic_cultures'` → `'culture_generic'`
- `'thermophilic lactic cultures'` → `'culture_generic'`
- `'mesophilic_starter'` → `'culture_generic'`
- `'yogurt cultures'` → `'culture_generic'` (for cheese)

### 5 enrich errors → All map to 'std_enriched'
- `{'vitamin_A': 'added', 'vitamin_D': 'added'}` → `'std_enriched'`
- Unknown `vitamin_A` / `vitamin_D` params → `'std_enriched'`

### 1 coagulate error → Map to 'milk'
- `'whole_milk'` → `'milk'`

**Result:** 13/13 rejections → 13 successful mappings (100% remediation)

## Next Steps for You

### 1. Delete Rejected Mappings
```bash
cd /Users/daveriedl/git/food-graph
# Backup current mappings
cp data/evidence/fdc-foundation/evidence_mappings.jsonl data/evidence/fdc-foundation/evidence_mappings.backup.jsonl

# Remove rejected entries
grep -v '"rejected"' data/evidence/fdc-foundation/evidence_mappings.jsonl > data/evidence/fdc-foundation/evidence_mappings.clean.jsonl
mv data/evidence/fdc-foundation/evidence_mappings.clean.jsonl data/evidence/fdc-foundation/evidence_mappings.jsonl

# Check count
wc -l data/evidence/fdc-foundation/evidence_mappings.jsonl
# Should be 114 lines (127 - 13 rejected)
```

### 2. Re-run Evidence Mapping
```bash
cd /Users/daveriedl/git/food-graph
pnpm evidence:map --resume
```

The script will:
1. Detect 13 missing foods (the ones you deleted)
2. Process them through Tier 2
3. Hit validation errors (same as before)
4. **NEW:** Route to Tier 3 for remediation
5. Apply bucketing philosophy
6. Save with corrected TPTs

### 3. Check Results
```bash
# Count rejections (should be 0 or very few)
grep -c '"rejected"' data/evidence/fdc-foundation/evidence_mappings.jsonl

# Check remediation messages
grep "Tier 3 remediation" data/evidence/fdc-foundation/evidence_mappings.jsonl | head -5

# Verify TPT IDs were generated
grep "tpt_id" data/evidence/fdc-foundation/evidence_mappings.jsonl | grep -v "null" | wc -l
```

### 4. Monitor Tier 3 Output
Watch for console output:
```
[VALIDATION] → X error(s) detected
[TIER 3] → Attempting remediation...
[TIER 3] → Strategy: map, Confidence: 0.90
[TIER 3] → ✓ Remediation successful: tx:a:bos:taurus|part:cheese:hard|abc123
```

## What to Watch For

### Good Signs ✅
- Tier 3 uses `"strategy": "map"` for most cases
- Confidence scores 0.85-0.95
- TPT IDs generated successfully
- Foods bucket together (same hash for similar foods)

### Warning Signs ⚠️
- Tier 3 frequently proposes `"expand"` strategy
- Low confidence (<0.7)
- Remediation failures
- Different cheeses getting different TPT hashes

## Rollback Plan

If something goes wrong:
```bash
# Restore original mappings
cp data/evidence/fdc-foundation/evidence_mappings.backup.jsonl data/evidence/fdc-foundation/evidence_mappings.jsonl

# Check git diff
git diff etl/evidence/
```

All changes are in these files:
- `etl/evidence/lib/optimized_prompts.py`
- `etl/evidence/lib/tier3_curator.py`
- `etl/evidence/lib/schema_validator.py`
- `etl/evidence/evidence_mapper.py`

## Success Metrics

**Primary:**
- Rejection rate: 10.2% → <2%
- All 13 current rejections successfully remediated

**Secondary:**
- No new rejections introduced
- TPT hash consistency maintained
- Processing time increase <20%

---

**Status:** ✅ Implementation Complete
**Next:** User testing with rejected foods

