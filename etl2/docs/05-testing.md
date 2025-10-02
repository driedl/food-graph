# Testing

We use **pytest**. The harness focuses on speed and determinism.

## Test types

1. **Smoke**: run a thin slice of the pipeline (e.g., A→B→E) and assert artifacts exist + minimal shape.
2. **Golden**: compare stage outputs (e.g., `tmp/transforms_canon.json`) to committed snapshots.
3. **Determinism**: run the same inputs twice → assert cache hits, identical bytes.
4. **Contracts**: jsonschema validation of outputs (e.g., `out/tpt_meta.jsonl`).

## Commands

```bash
pytest -q
pytest -q tests/test_smoke.py::test_cli_roundtrip
```

CI should run smoke + golden by default; determinism tests can be a scheduled job.
