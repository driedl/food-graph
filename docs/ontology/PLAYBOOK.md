
# Ontology Playbook

## Add a species in 3 steps
1. **Find lineage** (domain → kingdom → … → genus → species).
2. **Append NDJSON line** under `data/ontology/taxa/*.jsonl` with:
   ```json
   {"id":"tx:plantae:rosaceae:malus:domestica","parent":"tx:plantae:rosaceae:malus","rank":"species","display_name":"Apple","latin_name":"Malus domestica","aliases":["apple"],"tags":["foundation"]}
   ```
3. Run `pnpm ontology:lint` and fix any errors.

## Modeling tricky cases
### Greek yogurt
- Taxon stays at `Bos taurus → Milk → Yogurt` **species-level taxon** (taxon does not encode style).
- Identity comes from transforms/attributes:
  - `tf:strain` (whey removal)
  - `attr:style="greek"` (identity parameter)

### Enriched/00 flour
- Base species: `tx:plantae:poaceae:triticum:aestivum`
- Identity params:
  - `tf:mill` with `attr:refinement="00"|"refined"|"whole"`
  - `tf:enrich` with `attr:enrichment="std_enriched"|...`

### Canned tomatoes (salted vs no-salt)
- Species: `tx:plantae:solanaceae:solanum:lycopersicum`
- Identity param: `tf:brine` with `attr:salt_level="regular"|"low_salt"|"no_salt"`
- Resulting FoodStates differ by sodium and water content; evidence should not merge these.

## Ground rules
- If an attribute changes nutrients meaningfully at serving scale → treat as **identity**.
- If it’s metadata for provenance or minor variability → **covariate/facet**.
