# Nutrition Graph Documentation Index

_Last updated: 2025-09-30_

Start here, then follow the numbered docs in order.

## Core Documentation

1. [00_VISION](./00_VISION.md) — Project vision and principles
2. [01_ARCHITECTURE](./01_ARCHITECTURE.md) — Core entities, edges, and persistence
3. [02_ONTOLOGY_KIT](./02_ONTOLOGY_KIT.md) — Authoring formats and ETL pipeline
4. [03_ID_CONVENTIONS](./03_ID_CONVENTIONS.md) — ID shapes and stability policy
5. [04_ATTRIBUTES](./04_ATTRIBUTES.md) — Attribute roles and promotion policy
6. [05_TRANSFORMS](./05_TRANSFORMS.md) — Transform families, params, and math
7. [06_EVIDENCE_MODEL](./06_EVIDENCE_MODEL.md) — Evidence types and rollups (planned)
8. [07_ROADMAP](./07_ROADMAP.md) — Implementation phases and current focus
9. [08_PRIORS_EMBEDDINGS](./08_PRIORS_EMBEDDINGS.md) — Phylogenetic priors + nutrient embeddings (planned)
10. [09_CLASSIFICATIONS_AND_OVERLAYS](./09_CLASSIFICATIONS_AND_OVERLAYS.md) — Regulatory/market taxonomies (planned)
11. [10_QA_GUARDS](./10_QA_GUARDS.md) — Quality checks and reports (planned)
12. [11_STORAGE_AND_ARTIFACTS](./11_STORAGE_AND_ARTIFACTS.md) — Repo structure and build outputs
13. [12_RULES_APPLICABILITY](./12_RULES_APPLICABILITY.md) — Part and transform applicability system
14. [13_MONOREPO_OPTIMIZATION](./13_MONOREPO_OPTIMIZATION.md) — Technical debt analysis
15. [14_TAXON_PART_SEARCH_PROPOSAL](./14_TAXON_PART_SEARCH_PROPOSAL.md) — Taxon+part search design proposal

## ADRs (Architecture Decision Records)

- [0001-foodstate-identity-is-path](./adr/0001-foodstate-identity-is-path.md) — Why paths, not UUIDs
- [0002-fdc-as-evidence-not-identity](./adr/0002-fdc-as-evidence-not-identity.md) — Evidence vs identity separation

## Guides & References

- [How to Add Food](./how-to-add-food.md) — Step-by-step guide for curators
- [FDC Foundation Import](./sources/FDC_FOUNDATION_IMPORT.md) — FDC curation guide
- [CONTRIBUTING](../CONTRIBUTING.md) — Contribution guidelines

## Quick Start (Dev)

```bash
# Install dependencies
pnpm install

# Build database from ontology
pnpm etl:build

# Start API + Web
pnpm dev

# Or start individually
pnpm dev:api    # API on :3000
pnpm dev:web    # Web on :5173
```

## For AI Agents

See [agent/AGENT_GUIDE.md](../agent/AGENT_GUIDE.md) for a comprehensive quick reference with:

- Database schema and queries
- API endpoints
- Command reference
- Ontology structure
- Common patterns
