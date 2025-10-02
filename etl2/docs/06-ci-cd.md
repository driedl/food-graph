# CI / CD

Recommended GitHub Actions outline:

- **Check**: `pip install -e etl2[dev]`, `pytest -q`.
- **Build**: `python -m mise run` (all stages) on pushes to `main` and PRs labeled `build`.
- **Artifacts**: upload `etl2/build/out/*` and `etl2/build/database/graph.dev.sqlite`.
- **Cache**: use a cache key derived from `hashFiles('data/ontology/**', 'etl2/mise/**')`.

Gate merges on tests + lints only; DB creation is fast enough to run per‑PR in this phase.
