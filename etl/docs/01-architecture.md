# Architecture

```
sources/ (repo)
  └─ data/ontology/{taxa,parts,transforms,rules,...}

mise (runner)
  ├─ cli.py        # CLI commands: run, test
  ├─ io.py         # JSON/JSONL IO, atomic writes, hashing, glob helpers
  ├─ config.py     # Path resolution from envs
  └─ stages/       # Stage modules

build/ (artifacts)
  ├─ compiled/     # persistent ontology compilation (taxa, assets, docs)
  ├─ tmp/          # intermediate, diffable
  ├─ out/          # API-ready payloads (search docs, families catalog, tpt meta)
  ├─ graph/        # edges/substrates
  ├─ database/     # graph.dev.sqlite and companions
  └─ report/       # lint.json, stage_reports/*.json, timings
```

## Stage execution

- Each stage is a Python module with a `run()` function
- Stages are executed sequentially via CLI commands
- Artifacts are written **atomically** via temp‑files + rename
- Contract verification ensures stage outputs meet specifications

## Error handling

- Stages fail **closed**. Outputs are only visible if the whole stage succeeds.
- Lint findings are emitted to `build/report/lint.json` and stage reports under `build/report/stages/`.
