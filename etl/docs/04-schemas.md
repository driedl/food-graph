# Schemas

We validate inputs with JSON Schema (Draft 2020‑12) and perform cross‑ref checks.

**Key Schemas** (filenames indicative):
- `schema/part.schema.json` — add `parent_id`
- `schema/transform.schema.json` — add `order`, `class`, `params[].identity_param`
- `schema/flag_rule.schema.json` — guarded flags with `allOf`/`anyOf`/`noneOf` and param comparisons

**Rule Files**
- `rules/promoted_parts.jsonl`
- `rules/transform_applicability.jsonl`
- `rules/parts_applicability.jsonl`
- `rules/families.json`
- `rules/family_allowlist.jsonl`
- `rules/param_buckets.json`
- `rules/diet_safety_rules.jsonl`
- `rules/name_overrides.jsonl`
- `rules/taxon_part_synonyms.jsonl`

Validation outputs go to `build/report/lint.json`.
