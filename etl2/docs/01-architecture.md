# Architecture

```
sources/ (repo)
  └─ data/ontology/{taxa,parts,transforms,rules,...}

mise (runner)
  ├─ dag.py        # Stage, Dag, DagRunner, caching (hash(inputs + code))
  ├─ cli.py        # Typer commands: plan, run, clean, print-paths
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

## DAG & caching

- Each stage declares:
  - **inputs** (files/globs + optional upstream stage outputs)
  - **outputs** (declared files)
  - **params** (structured options included in hash)
  - **code‑fingerprint** (hash of the stage module)

- The runner computes a **fingerprint**; if identical to last run, the stage **skips** (cache hit).
- Artifacts are written **atomically** via temp‑files + rename.

## Error handling

- Stages fail **closed**. Outputs are only visible if the whole stage succeeds.
- Lint findings are emitted to `build/report/lint.json` and stage reports under `build/report/stages/`.
