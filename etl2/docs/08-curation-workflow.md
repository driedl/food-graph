# Curation Workflow

Curated data lives under `data/ontology/rules/**`. The linter enforces:

- Valid taxon/part/transform references
- Family coverage for curated TPTs
- Promoted parts use only part‑changing transforms in `proto_path`
- Guarded diet/safety rules reference actual params

**PR labels**
- `derived:add`, `derived:edit`, `derived:deprecate`
- `rules:update`
- `ontology:taxa`

**Golden data**
- Bacon, pancetta, yogurt/Greek/labneh, tofu, ghee, EVOO/refined oil, kimchi/sauerkraut
