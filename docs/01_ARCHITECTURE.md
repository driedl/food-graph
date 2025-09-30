# 01 — Architecture (Graph Model)

## Core Entities

- **Taxon**: lineage nodes (root → … → species). Examples: `tx:plantae:poaceae:oryza:sativa`.
- **Commodity** (optional): market/edible concept anchored to taxa for ambiguous aggregates (e.g., “oyster mushrooms”, “mixed berries”).
- **Part**: anatomical/plant parts applicable to taxa (fruit, leaf, seed, muscle, milk, egg).
- **TransformType**: process definition with parameter schema (boil, roast, mill, brine, enrich, strain, press, skim).
- **FoodState**: **identity-bearing node** = (Taxon | Commodity) + Part + ordered Transform chain (with params).
- **Mixture**: recipe/formulation; weighted edges to FoodState or other Mixtures (DAG).
- **Product** (overlay): branded/packaged item. Either a black-box label (panel-only) or a partially decomposed mixture referencing canonical ingredients.
- **Nutrient**: registry of dimensions (id, unit).
- **Evidence**: assay/label/database row attached to FoodState or Mixture (with method, source, time, uncertainty).
- **Classification** (parallel labeling): regulatory/market taxonomies (HS/PLU/CFIA/EFSA), stored as labelings over nodes.

## Edges

- `is_a` (Taxon→Taxon) — the lineage.
- `has_part` (Taxon→Part) — allowed edible parts (optional constraint matrix).
- `defines` (TransformType→schema) — parameters and defaults.
- `derived_by` (FoodState→FoodState) — applying a TransformType (+params) to parent state.
- `mixture_of` (Mixture→ingredient) — ingredient edges with quantity and optional pre-transform.
- `has_evidence` (FoodState|Mixture→Evidence).
- `has_attribute` (FoodState|Mixture→Attribute) — facets/covariates (non-identity).
- `labeled_as` (Node→Classification) — parallel taxonomies (regulatory/market).
- `is_functional` (Node→FunctionalClass) — derived “functional” categories (oils, flours, cheeses).

## Identity

A FoodState ID is a **canonical path**:

```
fs://plantae/poaceae/oryza/sativa/part:grain/tf:mill{refinement=whole}/tf:cook{method=boil,fat_added=false}
```

- The path is semantic; a short param-hash suffix may be appended for uniqueness if necessary (not required in v0.1).
- Identity-bearing attributes are encoded inside transform params (or as explicit transform steps).
- Products do **not** create new canonical identities; they overlay or reference canonical nodes.

## Mixtures

Mixtures are first-class nodes and may reference other mixtures (DAG). Evaluation is topological with caching and version pins.

## Persistence

- **Git (authoritative)**: ontology files, transform schemas, nutrients, attributes, **classifications**, **functional classes**, synonym lists, **models** (retention/yield/priors), **vocab**.
- **SQLite (compiled)**:
  - **Implemented**: `nodes`, `synonyms`, `node_attributes`, `attr_def`, `attr_enum`, `taxon_doc`, `part_def`, `part_synonym`, `has_part`, `transform_def`, `transform_applicability`, `nodes_fts` (FTS5 search)
  - **Planned**: `foodstate`, `mixture`, `evidence`, `classifications`, `functional_class`, `labelings`, materialized rollups
- **API/UI** read from SQLite; if lost, rebuild from Git.
