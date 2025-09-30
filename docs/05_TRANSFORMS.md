# 05 — Transforms (Families, Params & Math)

Transforms represent processes that change state, composition, or water content. Identity-bearing transforms appear in FoodState IDs.

## Families (v0.1)

- `tf:cook` — params: `{method: enum(raw|boil|steam|bake|roast|fry|broil), fat_added: boolean}`
- `tf:brine` — params: `{salt_level: enum(no_salt|low_salt|regular)}`
- `tf:mill` — params: `{refinement: enum(whole|refined|pearled|00), oat_form?: enum(rolled|steel_cut)}`
- `tf:enrich` — params: `{enrichment: enum(none|std_enriched|custom)}`
- `tf:strain` — params: `{target_TS_pct: number, drain_time_min: number}`
- `tf:skim` — params: `{fat_pct: number}` (alias for `tf:standardize_fat`)
- `tf:press` — params: `{pressure_kPa: number, time_min: number}`

See `data/ontology/transforms.json` for the complete list (29 transform families defined).

## Transform Math (policy)

Let `x_n` be nutrient `n` per 100 g of the **input** state and `x'_n` the **output** after transform `T`.

- **Yield**: mass change factor `y` (edible output / input). Normalize to 100 g output:
  `x'_n = x_n / y`
- **Retention**: nutrient-specific retention factor `r_n(T, class, params)` applied before re-basing:
  `x'_n = (x_n * r_n) / y`
- **Adds/Removals**: salt, enrichment, draining:
  - Additive `a_n` per 100 g output: `x'_n += a_n`
  - Removal of water `Δwater`: renormalize macros, maintain mass closure.
- **Chaining**: apply in order; keep per-nutrient provenance of each step.

Retention/yield tables live in `models/` and are versioned; defaults are class-specific.

## Validation

- Params canonicalized (lowercase enums, bounded numbers).
- Cooking with `method='raw'` is an identity (no-op).
