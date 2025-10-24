# 00 — Vision & Principles

**Problem:** Nutrition datasets are flat and unstable; identity drifts with naming, and merging sources is brittle.

**Vision:** A **taxonomy-first Food Graph** where each edible thing is a canonical **FoodState** (biology + part + process), and
nutrient values are **evidence** that “fills” the graph. IDs are stable; evidence can grow and improve without churn.

## Why this approach
- Biological lineage predicts similarity; siblings diverge gradually.
- Parts and processes (transform chains) can be modeled **orthogonally**, avoiding combinatorial name explosions.
- Provenance stays attached to values; rollups are explainable.

## Core Principles
1. **Identity is structural.** A FoodState = (Taxon | Commodity) + Part + Transform chain.
2. **Git-first.** Ontology changes are code-reviewed diffs with validation.
3. **Evidence over assertion.** Numbers flow from evidence with explicit provenance and confidence.
4. **Small stable core; rich edges.** Taxonomy is slow-changing; transforms, mixtures, and evidence evolve freely.
5. **AI-assisted, human-guarded.** Agents propose; humans arbitrate identity-affecting changes.

## Personas
- **Builder**: deterministic compiles, stable IDs, fast read APIs.
- **Curator**: author NDJSON, review PRs, accept/reject merge proposals.
- **User**: explores the graph; needs clear provenance and predictable substitutions.
- **Agent**: maps strings → FoodState, proposes transforms/retention models, flags gaps.

## Success Criteria
- Stable IDs across builds; no accidental churn.
- New sources integrate by **adding evidence**, not by forking identity.
- UI can traverse graph with or without evidence coverage.
- Clear QA surfaces (coverage deltas, outliers, neighbor checks).

## Current Capabilities

The Food Graph currently provides:

- **Rich Ontology**: Comprehensive taxonomy, parts, and transforms
- **Evidence System**: 3-tier evidence mapping with nutrition data integration
- **ETL Pipeline**: Complete data processing pipeline with validation
- **Search System**: Full-text search across all entities
- **API**: Type-safe tRPC API with real-time capabilities
- **Web Interface**: Modern React-based user interface
- **Nutrition Queries**: Comprehensive nutrient data with rollup aggregation

## Non-goals (v0.1)
- Full automation of taxonomy from external DBs.
- Perfect transform physics; start with pragmatic retention/yield tables.
- Deterministic "one-click" FDC taxonomy generator (we curate instead).
