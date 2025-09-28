
# FDC Foundation Import (Plan)

Goal: Map each **FDC Foundation** item to a **FoodState**:
`(species taxon + part + identity transforms/attributes)` and emit nutrient evidence per 100 g.

## Mapping Steps
1. **Normalize name** → detect species using alias tables (taxonomy `aliases`).
2. **Infer part** (e.g., grain, leaf, milk, muscle) from name/category hints; default to species whole if unknown.
3. **Parse identity parameters** (style/greek, process raw/cooked, brine salt_level, mill refinement, enrich enrichment, fat_pct/lean_pct).
4. **Emit FoodState key** (deterministic ordered KV string) and attach FDC nutrient vector.
5. **Unknown lineage?** Append to `missing_taxa.json` with suggested genus/species candidates.

## Outputs
- `build/fdc_foundation_evidence.jsonl` — one line per FDC item with:
  ```json
  {"fdc_id":"12345","foodstate":"tx:plantae:poaceae:oryza:sativa|part:grain|process=raw|refinement=whole|enrichment=none","nutr":{"energy_kcal":...,"protein_g":...}}
  ```
- `build/missing_taxa.json` — list of taxa to add before next run.

## Acceptance
- ≥ 98% of FDC 411 map automatically to existing taxonomy after we seed the families in backlog.
- Sodium-bearing canned products resolve to distinct FoodStates via `salt_level`.
