# Contributing to Nutrition Graph

Thanks for improving the project! This repo is **Git-first**: ontology files (NDJSON/JSON) are authoritative; SQLite DBs are compiled artifacts.

## TL;DR

1. `pnpm install` (Node 20+, pnpm 9+, Python 3.10+)
2. Compile: `pnpm db:build` → `data/builds/graph.dev.sqlite`
3. Run locally: `pnpm dev` (API :3000, Web :5173)
4. Open a PR with a clear title and, when needed, an **ADR**.

## Ground rules

- **Identity is structural**: FoodState = (Taxon | Commodity) + Part + Transform chain. If you change identity semantics, add an ADR.
- **FDC and other sources are evidence** attached to canonical FoodStates; they do not define identity.
- Keep diffs small and focused; one concern per PR.

## Branch & commit style

- Branch: `feature/<topic>` or `fix/<topic>`
- Conventional commits are encouraged (feat:, fix:, docs:, chore:, refactor:, perf:, test:).

## Making ontology changes

- Edit NDJSON/JSON under `data/ontology/` (see `docs/02_ONTOLOGY_KIT.md`).
- Keep NDJSON as **one JSON object per line**. No trailing commas.
- Validate by compiling: `pnpm db:build` and checking API/UI.
- Never put process terms into taxonomy names; see `docs/03_ID_CONVENTIONS.md`.

## When to write an ADR

Create or update an ADR for:

- Identity rules (attributes ↔ transforms, FoodState path semantics)
- Schema evolution (attributes, transforms, evidence fields)
- Data policies (priors, embeddings use, QA thresholds)
- API/storage contracts (models/, vocab/, artifacts)

Use the template at `docs/adr/_TEMPLATE.md`. Start with **Status: Proposed**, then **Accepted** on merge.

## Review checklist (copy into your PR description)

- [ ] Docs updated (link to section or ADR)
- [ ] Compiles: `pnpm db:build` succeeded
- [ ] API starts (`pnpm dev:api`) and `GET /` returns ok
- [ ] UI loads and graph root resolves
- [ ] If identity-affecting: ADR added/updated
- [ ] If evidence added: source + method + basis documented

## Local environment

Set `DB_PATH` if you keep builds outside the repo root. Example `apps/api/.env`:

```
PORT=3000
DB_PATH=../../data/builds/graph.dev.sqlite
```

## Code style

- TypeScript strict; run `pnpm typecheck` and `pnpm lint`.
- Keep UI components small and headless; prefer composition over props explosion.

## Security & licensing

- Include source licenses in evidence where required.
- Do not commit proprietary datasets.

Happy graphing! 🧪🌿
