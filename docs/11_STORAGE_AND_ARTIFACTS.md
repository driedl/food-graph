# 11 — Storage Layout & Build Artifacts

## Repo Layout (Git)

```
data/
  ontology/
    taxa/
      **/*.tx.md            # Taxon markdown files with frontmatter
      **/*.jsonl            # Compiled intermediate JSONL
      index.jsonl           # Root taxa definitions
    parts.json
    transforms.json
    nutrients.json
    attributes.json
    animal_cuts/            # Hierarchical animal part definitions
      *.json
    rules/                  # Applicability rules
      parts_applicability.jsonl
      transform_applicability.jsonl
  vocab/                    # synonyms, external IDs (future)
  models/                   # retention/yield, priors, embeddings (future)
```

- **Taxa**: Organized by kingdom/phylum/family hierarchy as `.tx.md` files with YAML frontmatter
- `vocab/`: free-text → (node, confidence), multi-locale (future)
- `models/`: versioned with metadata (`model_id`, date, source) (future)

## Build Artifacts

- `etl/dist/database/graph.dev.sqlite` — API DB
- `reports/id_churn.json` — IDs added/removed (planned)
- `reports/qa/*.json` — QA outputs
- `models/<model_id>/...` — embeddings, priors, tables (optional)

## Reproducibility

Record `git_sha` + `model_ids` per build; APIs accept `?model_id=` to pin behavior.
