Here’s a fresh, drop-in **README.md** for the repo root that matches the new docs + current code. Paste it over your existing README.

---

# Nutrition Graph

A monorepo starter for building a **taxonomy-first food & nutrition graph** with a React explorer UI and a Fastify/tRPC API backed by SQLite.
Identity is defined by **(Taxon | Commodity) + Part + Transform chain**; nutrient values are **evidence** that “fills” the graph.

- Web: Vite + React + Tailwind + React Flow
- API: Fastify + tRPC + better-sqlite3
- Data: Git-first ontology (NDJSON/JSON) → compiled to SQLite via a tiny ETL

👉 Start with the docs: **[`docs/INDEX.md`](./docs/INDEX.md)**

---

## Quick start

```bash
# prerequisites: Node 20+, pnpm 9+, Python 3.10+
pnpm install

# (one-time if needed) normalize NDJSON line endings
# python script is optional; see docs/02_ONTOLOGY_KIT.md
# pnpm ontology:fix-newlines

# compile ontology → SQLite
pnpm db:build     # writes ./data/builds/graph.dev.sqlite

# run API + Web (concurrently via Turbo)
pnpm dev
```

- API: [http://localhost:3000](http://localhost:3000)
- Web: [http://localhost:5173](http://localhost:5173)

> If the compiled DB is missing, the API seeds a tiny scaffold (Life + kingdoms) so the explorer still loads.

---

## Monorepo layout

```
apps/
  api/                  # Fastify + tRPC + better-sqlite3
  web/                  # Vite React UI, React Flow explorer
etl/
  py/                   # lightweight compiler & utilities
data/
  ontology/             # NDJSON/JSON ontology sources (authoritative)
  builds/               # compiled SQLite DB(s) (artifacts)
docs/                   # project documentation (start at INDEX.md)
packages/
  shared/               # shared TS types
```

---

## Scripts

At repo root:

- `pnpm dev` — run API + Web together (Turbo pipeline)
- `pnpm dev:api` / `pnpm dev:web` — run individually
- `pnpm db:build` — compile ontology → `data/builds/graph.dev.sqlite`
- `pnpm db:open` — open the current DB in `sqlite3`
- `pnpm lint` / `pnpm typecheck` — standard hygiene

> If you prefer not to use Turbo, you can run `pnpm -C apps/api dev` and `pnpm -C apps/web dev` in separate terminals.

---

## Environment

The API looks for a SQLite DB path:

- **Env var:** `DB_PATH`
- **Default (if unset):** `<process.cwd()>/data/builds/graph.dev.sqlite`

Because `apps/api` runs from its own working directory, we recommend setting an explicit path.

Create `apps/api/.env`:

```env
# API server
PORT=3000

# Point to the compiled DB at repo root
DB_PATH=../../data/builds/graph.dev.sqlite
```

(Alternatively, keep the default and compile into `apps/api/data/builds/…`.)

---

## What’s in the DB (v0.1)

The current compiler ingests **Taxa + Synonyms + Attribute registry**:

- `nodes(id, name, slug, rank, parent_id)`
- `synonyms(node_id, synonym)`
- `attr_def(attr, kind)`
- (`node_attributes` reserved for future authoring)

Future versions add `foodstate`, `mixture`, `evidence`, transform defs, rollups, and QA reports. See **`docs/11_STORAGE_AND_ARTIFACTS.md`**.

---

## Architecture at a glance

- **Taxon** tree (root → species), **Parts**, **TransformType** definitions
- **FoodState** = (Taxon | Commodity) + Part + Transform chain (identity)
- **Mixture** nodes (recipes, can reference other mixtures)
- **Evidence** attaches to FoodStates/Mixtures; rollups compute canonical panels
- **Parallel classifications** (HS/PLU/etc.) and **functional classes** (oils, flours) are overlays—never identity

Details: **`docs/01_ARCHITECTURE.md`**, **`docs/04_ATTRIBUTES.md`**, **`docs/05_TRANSFORMS.md`**.

---

## Developing in Cursor

- Types live in `packages/shared/src`.
- tRPC types flow to the UI automatically (`apps/web/src/lib/trpc.ts`).
- Graph explorer: `apps/web/src/components/GraphView.tsx` (React Flow).
- API endpoints: `apps/api/src/router.ts` (health, taxonomy browse/search).

---

## Troubleshooting

- **UI loads but graph is empty** → compile the ontology: `pnpm db:build` (and confirm `DB_PATH`).
- **NDJSON errors** → run the newline fixer (see `docs/02_ONTOLOGY_KIT.md`).
- **Ports in use** → set `PORT` in `apps/api/.env` and update the web proxy in `apps/web/vite.config.ts` if needed.

---

## Documentation map

- Start: **`docs/INDEX.md`**
- Vision & principles: `docs/00_VISION.md`
- Ontology kit & authoring: `docs/02_ONTOLOGY_KIT.md`
- IDs & stability: `docs/03_ID_CONVENTIONS.md`
- Attributes & transforms: `docs/04_ATTRIBUTES.md`, `docs/05_TRANSFORMS.md`
- Evidence, priors, embeddings, QA: `docs/06_EVIDENCE_MODEL.md`, `docs/08_PRIORS_EMBEDDINGS.md`, `docs/10_QA_GUARDS.md`
- Roadmap: `docs/07_ROADMAP.md`
- FDC stance: `docs/sources/FDC_FOUNDATION_GUIDE.md` (inspired by 411 → curated evidence)

---

## License

TBD.

---

If you want, I can also generate a tiny `CONTRIBUTING.md` and an `ADR` starter (`docs/adr/0001-foodstate-identity-is-path.md`) to lock the big decisions.
