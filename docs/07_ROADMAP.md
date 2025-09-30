# 07 — Roadmap (Ontology & Data)

## Phase 0 — Tooling & Governance ✅ COMPLETE

- ✅ NDJSON format with `.tx.md` frontmatter compilation
- ✅ Python ETL pipeline with validation, compilation, and verification
- ✅ Schema validation (parent existence, acyclicity checks)
- ✅ FTS5 search infrastructure

## Phase 1 — Coverage (In Progress)

- 🔄 Expand taxonomy: 200+ taxa across plantae, animalia, fungi
- 🔄 Animal parts system with applicability rules
- 🔄 Plant families and common cultivars
- 📝 FDC Foundation alignment (planned)

## Phase 2 — Transforms & Attributes ✅ COMPLETE

- ✅ Identity-bearing attributes locked (roles: identity_param, covariate, facet)
- ✅ 29 transform families defined with param schemas
- ✅ Transform applicability rules system
- ❌ Default retention/yield tables (deferred to Phase 3)

## Phase 3 — Evidence & Canonicalization (Planned)

- FoodState materialization (currently computed on-demand)
- Evidence tables and provenance tracking
- FDC Foundation as evidence mapped to FoodStates
- Per-nutrient rollups with hierarchical borrowing

## Phase 4 — QA & Signals (Planned)

- Distance-based split candidates
- Sodium/water guards
- Mass closure validation
- Embedding-based anomaly detection

## Phase 5 — Recipes & Mixtures (Planned)

- Mixture DAG evaluation
- Nested mixtures with version pinning
- Public/user namespaces

## Current Focus

- [ ] Taxon+part search nodes (see doc 14)
- [ ] Documentation coverage (166 taxa documented)
- [ ] Transform chains for common derived foods
- [ ] Evidence model implementation
