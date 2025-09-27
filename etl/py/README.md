# Ontology Kit v1 (Nutrition Graph)

Git-first, DB-compiled ontology for a food/nutrition graph.

## Structure
- `schema/` — JSON Schemas for human review & future validation.
- `seed/` — Seed ontology data (JSON). Extend via PRs.
- `build/` — Compiler outputs (SQLite DB + reports).
- `compile.py` — Lightweight compiler that validates and builds a portable SQLite DB.

## Quick Start
```bash
python compile.py --in ./seed --out ./build/foodgraph.sqlite
```

Outputs:
- `build/foodgraph.sqlite` — browse-ready DB (taxa, parts, transforms, attributes, nutrients)
- `build/id_map.json` — stable IDs for this compile
- `build/id_churn_report.json` — comparison vs previous run (if any)

## ID Philosophy
- IDs are **human-readable** and **stable** (e.g., `tx:plantae:poaceae:oryza:sativa`).
- No source-specific IDs; evidence from any datasource attaches later.
- Transform families are declared but FoodState nodes are created by ingesters/authoring tools later.

## Next Steps
- Add more taxa/parts/transforms incrementally.
- In the API/UI phase, read from `foodgraph.sqlite` to serve graph browsing.
- Evidence ingesters (FDC, CIQUAL, branded labels) will bind to nodes and emit nutrients at node scope or mixture scope.
