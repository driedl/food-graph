# ADR 0002: FDC Foundation is evidence, not identity

- **Status:** Accepted
- **Date:** 2025-09-28
- **Owners:** @maintainers
- **Decision Drivers:** canonical graph stability; provenance; license and mapping differences across sources

## Context
The FDC Foundation 411 list is a useful coverage compass and source of nutrient values, but product forms and naming vary. Using FDC rows to mint canonical IDs would entrench source-specific quirks and cause churn.

## Decision
Treat FDC (and similar datasets) as **evidence** attached to canonical FoodStates. We **do not** generate canonical taxonomy or FoodState IDs deterministically from FDC. We curate mappings from FDC rows → `(Taxon | Commodity) + Part + identity-bearing Transforms` and attach per-nutrient vectors with full provenance.

## Options Considered
- **Deterministic generation of canonical nodes from FDC:** faster bootstrap, but bakes in source noise and weak identity semantics.
- **Manual curation only:** precise but slow.
- **Agent-assisted curation (chosen):** agents propose mappings; humans arbitrate identity-affecting cases.

## Consequences
- ✅ Stable canonical IDs; sources can evolve without identity churn.
- ✅ Clear separation of identity vs evidence; provenance is explicit.
- ⚠️ Requires and invests in mapping dictionaries and QA.
- ❌ Slightly slower initial throughput vs naive generation.

## Implementation Notes
- Follow `docs/sources/FDC_FOUNDATION_GUIDE.md` for workflow and acceptance criteria.
- Store evidence as JSONL with `source`, `method`, `release`, and 100 g edible basis.
- Mark ambiguous mappings with `tags: ["needs_taxonomy"]` for review.
- Keep importer scripts optional and idempotent.

## References
- docs/sources/FDC_FOUNDATION_GUIDE.md
- docs/06_EVIDENCE_MODEL.md
