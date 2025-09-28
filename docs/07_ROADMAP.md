# 07 — Roadmap (Ontology & Data)

## Phase 0 — Tooling & Governance
- NDJSON format, newline fixer, basic compiler.
- CI: validate schemas, parent existence, acyclicity (planned).

## Phase 1 — Coverage
- Pantry-100 complete; fill missing parents for FDC 411 alignment.
- Add common animal cuts and key plant families.

## Phase 2 — Transforms & Attributes
- Lock identity-bearing attributes; finalize v0.1 transform families.
- Add param schemas and default retention/yield tables (by class).

## Phase 3 — Evidence & Canonicalization
- Curate FDC Foundation as **evidence** mapped to FoodStates (no auto generation).
- Implement per-nutrient rollups with provenance.

## Phase 4 — QA & Signals
- Distance-based split candidates; sodium/water guards; mass closure.

## Phase 5 — Recipes & Mixtures
- Mixture authoring, nested mixtures, yield handling; public/user namespaces.

### Near-term Checklist
- [ ] Normalize NDJSON newlines where needed.
- [ ] Compile and browse graph (root = `tx:life`).
- [ ] Add exemplar FoodStates and mock evidence.
- [ ] Draft retention tables for `tf:cook` on key classes.
