# 03 — ID Conventions & Stability

## ID Shapes

- **Taxa**: `tx:<path>` using lowercase ASCII, colon-separated:
  - `tx:life`
  - `tx:eukaryota`
  - `tx:plantae:poaceae:oryza:sativa`
- **Parts**: `part:<slug>` (e.g., `part:fruit`, `part:grain`, `part:milk`).
- **Transforms**: `tf:<slug>` (e.g., `tf:brine`, `tf:mill`, `tf:enrich`, `tf:strain`, `tf:cook`).
- **Attributes**: `attr:<slug>` (e.g., `attr:salt_level`, `attr:refinement`).
- **Nutrients**: `nutr:<slug>` (e.g., `nutr:protein_g`).

## Ranks

Allowed: `root | domain | kingdom | phylum | class | order | family | genus | species | cultivar | variety | breed | product | form`

## Naming Rules

- `display_name` is human-facing; `latin_name` is scientific where applicable.
- **Do not** put process terms or identity parameters in taxonomy names or aliases.
  - Avoid: raw, cooked, baked, fried, canned, brined, strained, greek, enriched, refined, 00, 2%.
- Aliases: lowercase, simple strings, meaningful variants; avoid duplicates of display names.

## Stability Policy

- IDs are **stable once merged**. Spelling fixes go to `display_name` or `aliases`.
- If a node must be replaced, mint a new ID and add `deprecated_of: <new_id>` on the old node (future tooling will surface this).

## FoodState IDs

- Path-like, semantic; include Part and ordered transforms with **identity-bearing** params:
  ```
  fs://plantae/poaceae/oryza/sativa/part:grain/tf:mill{refinement=whole}/tf:cook{method=boil}
  ```
- If params are long, append an opaque short suffix solely for uniqueness (not required in v0.1).
