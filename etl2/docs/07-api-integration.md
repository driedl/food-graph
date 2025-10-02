# API Integration

The API selects the build via envs and can switch between legacy and mise without code changes.

- `GRAPH_DB_PATH` → SQLite database path to open.
- `GRAPH_BUILD_ROOT` → Where to find JSONL deliverables (`out/search_docs.jsonl`, `out/tpt_meta.jsonl`, etc.).

Example dev setup:

```bash
# legacy
GRAPH_DB_PATH=etl/dist/database/graph.dev.sqlite pnpm dev

# mise
GRAPH_DB_PATH=etl2/build/database/graph.dev.sqlite pnpm dev
```
