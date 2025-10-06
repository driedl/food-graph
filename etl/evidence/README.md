# Evidence Toolkit (POC)

**Goal:** quick-and-dirty mapping of FDC FOUNDATION foods → FoodState identity proposals using an LLM, and
dumping normalized evidence as JSONL (no DB writes here). A later script (profiles.py) can insert evidence into the graph DB.

## Commands

```bash
# 1) Map FDC → JSONL + LLM mappings (FOUNDATION only, ~411 rows)
python -m etl2.evidence.map \    --graph etl2/build/database/graph.dev.sqlite \    --fdc data/sources/fdc \    --out data/evidence/fdc-foundation \    --model gpt-5-mini \    --min-conf 0.70 \    --topk 15 \    --limit 0

# 2) (Later) Materialize profiles into the DB from JSONL (stub)
python -m etl2.evidence.profiles \    --graph etl2/build/database/graph.dev.sqlite \    --evidence data/evidence/fdc-foundation \    --accept-threshold 0.70
```

## Outputs
- `foods.jsonl` — FOUNDATION foods (filtered)
- `nutrients.jsonl` — per-food nutrient rows (restricted to selected foods)
- `mapping.jsonl` — LLM-produced identity proposals per food
- `_proposals/` — optional “new taxon/part/transform” suggestions (not applied)
- `logs/map.log` — run log

## Notes
- We **only** map FDC foods where `data_type == "Foundation"` and we try to **skip obviously processed** items
  via category/name heuristics. This keeps the POC focused on 411 “foundation” foods with full panels.
- The script **reads** the compiled `graph.dev.sqlite` to:
  - Fetch **parts** and **transforms** to prime the prompt
  - Run **FTS candidate search** (`search_fts`) to ground the LLM
- No SQLite writes occur here; we only write JSONL. The later `profiles.py` handles DB insertion.
- You can adjust skip heuristics in `etl2/evidence/lib/fdc.py` or provide your own allow/deny lists under
  `data/evidence/_registry/` (see placeholders).
