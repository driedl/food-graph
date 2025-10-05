# CI / CD

Recommended GitHub Actions outline:

- **Check**: `pip install -e etl[dev]`, `pytest -q`.
- **Build**: `python -m mise run` (all stages) on pushes to `main` and PRs labeled `build`.
- **Artifacts**: upload `etl/build/out/*` and `etl/build/database/graph.dev.sqlite`.
- **Cache**: use a cache key derived from `hashFiles('data/ontology/**', 'etl/mise/**')`.

Gate merges on tests + lints only; DB creation is fast enough to run per‑PR in this phase.
