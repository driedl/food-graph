# 04 — Attributes: Roles & Policy

Attributes are classified by **role**. The role determines whether an attribute affects **identity** (and thus FoodState IDs).

## Roles
1. **identity_param** — Encoded in transforms (or taxon refinements). Changes nutrients in a predictable, material way.
   - Examples: `style=greek` (strain), `salt_level`, `refinement`, `enrichment`, `fat_pct`, `lean_pct`, `process` (as a param of `tf:cook`).
2. **taxon_refinement** — Rare; used when taxonomy needs an internal refinement axis (e.g., registered cultivar). Typically model as a child taxon instead.
3. **covariate** — Influences evidence selection/weighting, **not identity**.
   - Examples: `ripeness_bucket`, `region`, `season`, `lab_code`.
4. **facet** — Discovery-only metadata.
   - Examples: `color`, `brand`.

## Identity vs Metadata — Examples
- **Greek yogurt**: identity via `tf:strain` with `style=greek` (identity-bearing).
- **Canned tomatoes**: identity via `tf:brine{salt_level}`.
- **Wheat flour**: identity via `tf:mill{refinement}` + `tf:enrich{enrichment}`.
- **Banana ripeness**: `ripeness_bucket` is a **covariate** unless specific transforms with measurable effects are defined.

## Promotion/Demotion Policy
- Start conservative: prefer `covariate` unless strong evidence shows material nutrient differences.
- **Promote** to `identity_param` (or add a transform) once data supports it. This creates new FoodStates without breaking existing ones.
