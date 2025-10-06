# TPT ETL Plan (condensed, actionable)

This document maps the TPT implementation vision into concrete graph stages and artifacts.

## Goals
- T, TP, and TPT are first‑class in search and navigation.
- Parameter‑aware identity hashing (only identity params contribute).
- Guarded diet/safety flags evaluated from transforms and params.

## Key outcomes
- Unified search corpus over TP/TPT/Promoted Parts
- Curated TPT catalog with identity hashes
- Deterministic IDs: `tpt:<taxon>:<part>:<family>:<hash>`

## Stage mapping
- **A**: Normalize transforms (add `order`, `class`, `identity_param`), validate flags schema, fix tofu/press edge; emit `tmp/transforms_canon.json` and `report/lint.json`.
- **B**: Materialize substrates using parts applicability (builtin + rules) and promoted parts; emit `graph/substrates.jsonl`.
- **C**: Ingest curated derived foods; validate against substrates; strip non‑identity steps.
- **D**: Templatize families (CULTURED_DAIRY, DRY_CURED_MEAT, etc.) with allowlist; emit `tmp/tpt_generated.jsonl`.
- **E**: Canonicalize paths (sort by `order`, bucket params); compute `identity_hash`; emit `tmp/tpt_canon.jsonl`.
- **F**: Names/synonyms/cuisines; emit `tmp/tpt_named.jsonl`.
- **G**: Evaluate diet/safety via guarded rules; update `tmp/tpt_named.jsonl`.
- **H**: Build edges (`graph/edges.jsonl`).
- **I**: Build `out/tpt_meta.jsonl` (denormalized cards).
- **J**: Build `out/search_docs.jsonl` (types: tp, tpt, part).
- **K**: Build `database/graph.dev.sqlite` (FTS over taxa + TP; TPT integrated later).

## Errors (fail closed on curated items)
- E001: invalid transform in path (non‑identity or not applicable)
- E002: missing T×P substrate
- E003: family not resolvable
- E004: promoted part uses identity TF
- E005: ID collision
- E006: unsafe/ambiguous flags inference

## Golden set (tests)
- Bacon (dry cure + cold smoke, nitrite present)
- Pancetta (dry cure, no smoke)
- Yogurt/Greek/Labneh (strain levels)
- Tofu (plant milk → coagulate → press)
- Ghee (clarify butter)
- EVOO vs refined oil (refine_oil identity split)
- Kimchi/Sauerkraut (salt + ferment)
