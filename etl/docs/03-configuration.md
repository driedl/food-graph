# Configuration

`mise` is env‑first. Sensible defaults keep local dev simple.

| Env | Default | Purpose |
|-----|---------|---------|
| `GRAPH_BUILD_ROOT` | `etl2/build` | Base directory for artifacts |
| `GRAPH_DB_PATH` | `$GRAPH_BUILD_ROOT/database/graph.dev.sqlite` | Output DB path |
| `GRAPH_BUILD_PROFILE` | `dev` | Name of the profile (file‑names and reports may include it) |
| `GRAPH_SOURCES_ROOT` | `.` | Repo root for data/ontology paths |

Paths are configured via environment variables or command line arguments.
