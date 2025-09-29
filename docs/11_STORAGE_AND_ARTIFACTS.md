# 11 — Storage Layout & Build Artifacts

## Repo Layout (Git)

```
data/
  ontology/
    taxa/*.jsonl
    parts.json
    transforms.json
    nutrients.json
    attributes.json
  vocab/                    # synonyms, external IDs (future)
  models/                   # retention/yield, priors, embeddings (future)
```

- `vocab/`: free-text → (node, confidence), multi-locale.
- `models/`: versioned with metadata (`model_id`, date, source).

## Build Artifacts

- `etl/dist/database/graph.dev.sqlite` — API DB
- `reports/id_churn.json` — IDs added/removed (planned)
- `reports/qa/*.json` — QA outputs
- `models/<model_id>/...` — embeddings, priors, tables (optional)

## Reproducibility

Record `git_sha` + `model_ids` per build; APIs accept `?model_id=` to pin behavior.
