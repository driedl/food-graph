# 10 — QA Guards & Reports

## Checks
1. Mass closure (water + macros + ash ≈ 100 g).
2. Sodium/water sanity (brined/canned vs raw).
3. Within-node dispersion (IQR/SD thresholds).
4. Neighbor similarity (taxonomy-aware distances).
5. Unit/rounding normalization.
6. Transform reversibility cross-checks.
7. Outliers via robust z-scores / isolation forest on embeddings.

## Reports
- `qa/coverage.json`
- `qa/anomalies.jsonl`
- `qa/deltas.json` (rollup regressions)

## Severity & Policy
- Levels: info, warn, error.
- CI fails on **error** for core nutrients; warns for others.
