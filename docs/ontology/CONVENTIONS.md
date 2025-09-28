
# Ontology Conventions (Nutrition Graph)

This document defines **stable, git-first** conventions for the food taxonomy and related vocabularies.

## IDs & Names
- **Taxa**: `tx:<path>` using colon-separated lineage, lowercase ASCII, hyphen/underscore allowed. Examples:
  - `tx:life`
  - `tx:eukaryota`
  - `tx:plantae:poaceae:oryza:sativa`
- **Parts**: `part:<slug>` e.g., `part:fruit`, `part:grain`, `part:milk`, `part:muscle`
- **Attributes**: `attr:<slug>` e.g., `attr:process`, `attr:salt_level`, `attr:fat_pct`
- **Transforms**: `tf:<slug>` e.g., `tf:cook`, `tf:mill`, `tf:brine`, `tf:strain`
- **Nutrients**: `nutr:<slug>` e.g., `nutr:protein_g`

`display_name` is human-facing; `latin_name` is the scientific label where applicable. Use US English for display names.

## Ranks
We allow classic ranks and pragmatic buckets:
`root | domain | kingdom | phylum | class | order | family | genus | species | cultivar | variety | breed`

- Keep the graph **acyclic**; each taxon has at most one `parent`.
- If uncertain between `cultivar/variety`, prefer `variety` for plants unless a registered cultivar is known.

## What *not* to put in taxonomy names
**Process terms** and **identity parameters** belong to **attributes/transforms**, *not* taxonomy.
Examples to avoid in `display_name` or `aliases`:
- Process words: `raw`, `cooked`, `baked`, `fried`, `canned`, `brined`, `strained`, `greek`, `enriched`, `refined`, `00`, `2%`, `1%`, `nonfat`.
- Brand terms or packaging: `brand`, `organic` (use attributes if needed as covariates/facets).

## Aliases
- `aliases` are lowercase plain strings without punctuation noise; avoid duplicates of `display_name`.
- Include common names and spelling variants (e.g., `garbanzo` for chickpea).

## Stability & Churn
- IDs are **stable** once merged. Edits to spelling go to `display_name`/`aliases`.
- If a node must be *replaced*, create a new node and add `deprecated_of: <new_id>` on the old node (handled by tools later).

## Evidence Scope
- Nutrient evidence should attach to **FoodState** = `(species taxon + part + identity-bearing transforms/attributes)`.
- Identity-bearing attributes (examples): `process`, `salt_level`, `refinement`, `enrichment`, `style`, `fat_pct`, `lean_pct`.
- Non-identity (covariate/facet) attributes: `ripeness_bucket`, `region`, `lab_code`, `color`, `brand`.

## File Format
We keep large lists in **NDJSON** (`.jsonl`) files—one JSON object per line—for easy diffing.
