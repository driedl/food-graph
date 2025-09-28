# ADR 0001: FoodState identity = (Taxon|Commodity) + Part + Transform chain

- **Status:** Accepted
- **Date:** 2025-09-28
- **Owners:** @maintainers
- **Decision Drivers:** stable IDs; clear provenance; avoid name-based churn; process affects nutrients

## Context
Flat food tables churn IDs tied to strings (“Greek yogurt”, “canned tomato (no salt)”). We need stable identity that reflects biology + part + process.

## Decision
A FoodState’s identity is defined by a canonical path:
`(Taxon | Commodity) + Part + ordered Transform steps (with identity-bearing params)`.
Attributes that materially change nutrients (e.g., `style=greek`, `salt_level`, `refinement`, `enrichment`) are encoded as transform params. Non-material attributes are covariates/facets and do not affect identity.

## Options Considered
- **String-based IDs:** simple but brittle; merges/splits churn IDs.
- **Source-keyed IDs (FDC etc.):** quick bootstrap but not canonical; cross-source duplication.
- **Graph path (chosen):** stable, explainable; slightly more authoring overhead.

## Consequences
- ✅ Stable, explainable IDs; provenance by construction.
- ✅ Evidence can improve without changing identity.
- ⚠️ Requires transform/attribute discipline and tooling.
- ❌ Some historical datasets need mapping to path semantics.

## Implementation Notes
- Enforce attribute roles in `attributes.json` (`identity_param|covariate|facet`).
- Compiler validates transform params and path canonicalization.
- UI shows the path; API exposes it as the primary key.

## References
- docs/01_ARCHITECTURE.md
- docs/04_ATTRIBUTES.md
- docs/05_TRANSFORMS.md
