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
pnpm db:build     # writes ./etl/dist/database/graph.dev.sqlite

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
  api/                  # Fastify + tRPC + better-sqlite3 backend
    ├── src/            # TypeScript source code
    │   ├── db.ts       # Database connection & queries
    │   ├── index.ts    # Fastify server setup
    │   └── router.ts   # tRPC router & endpoints
    ├── migrations/     # SQL migration files
    │   ├── 0001_init.sql
    │   ├── 0002_nodes_fts.sql
    │   └── 0003_taxon_docs.sql
    └── dist/           # Compiled JavaScript output

  web/                  # Vite + React frontend with React Flow
    ├── src/
    │   ├── components/ # React components
    │   │   ├── GraphView.tsx     # Main graph visualization
    │   │   ├── ErrorBoundary.tsx # Error handling
    │   │   └── ui/              # Reusable UI components
    │   ├── lib/        # Utilities & tRPC client setup
    │   └── styles/     # CSS & Tailwind configuration
    └── index.html      # Entry point

packages/
  shared/               # Shared TypeScript types & interfaces
    └── src/index.ts   # TaxNode, NodeAttribute, NodeRank types

  api-contract/         # tRPC router type exports (no runtime)
    └── src/index.ts   # Re-exports AppRouter type for frontend

  config/              # Environment configuration & validation
    └── src/index.ts   # Zod schemas for env vars (NODE_ENV, PORT, DB_PATH)

data/
  ontology/            # Authoritative NDJSON/JSON ontology sources
    ├── taxa/          # Taxonomic hierarchy data
    │   ├── animalia/  # Animal taxa
    │   ├── fungi/     # Fungal taxa
    │   ├── plantae/   # Plant taxa (38 family files)
    │   └── docs/      # Taxonomic documentation (.tx.md files)
    ├── attributes.json # Attribute definitions
    ├── nutrients.json # Nutrient catalog
    ├── parts.json     # Food part definitions
    ├── transforms.json # Processing transform definitions
    └── compiled/      # Intermediate compilation artifacts

  builds/              # Final compiled SQLite databases
    ├── graph.dev.sqlite      # Main development database
    ├── id_churn_report.json  # ID mapping reports
    └── id_map.json          # ID translation mappings

  sources/             # External data sources
    └── fdc/           # USDA FoodData Central imports
        ├── food.csv
        ├── food_nutrient.csv
        ├── food_portion.csv
        └── nutrient.csv

  sql/                 # Database schema definitions
    └── schema/        # JSON schema files for validation

etl/                   # Data compilation pipeline
  └── py/             # Python ETL scripts
      └── compile.py  # Main ontology → SQLite compiler

scripts/               # Development & maintenance utilities
  ├── aggregate.ts    # Data aggregation tools
  ├── compile_docs.py # Documentation compilation
  ├── compile_taxa.py # Taxonomic data compilation
  ├── print-trpc-routes.ts # API route inspection
  ├── run-sql.ts      # SQL query execution
  ├── validate_ndjson.ts # NDJSON validation
  ├── validate_taxa.py # Taxonomic data validation
  └── ontology/       # Ontology-specific utilities
      ├── diff.ts     # Ontology diffing
      └── validate.ts # Ontology validation

docs/                  # Comprehensive project documentation
  ├── INDEX.md        # Start here - documentation overview
  ├── 00_VISION.md    # Project vision & principles
  ├── 01_ARCHITECTURE.md # System architecture
  ├── 02_ONTOLOGY_KIT.md # Ontology authoring guide
  ├── 03_ID_CONVENTIONS.md # ID naming & stability
  ├── 04_ATTRIBUTES.md # Attribute system design
  ├── 05_TRANSFORMS.md # Processing transforms
  ├── 06_EVIDENCE_MODEL.md # Evidence & nutrition data
  ├── 07_ROADMAP.md   # Development roadmap
  ├── 08_PRIORS_EMBEDDINGS.md # ML embeddings strategy
  ├── 09_CLASSIFICATIONS_AND_OVERLAYS.md # Classification systems
  ├── 10_QA_GUARDS.md # Quality assurance
  ├── 11_STORAGE_AND_ARTIFACTS.md # Storage architecture
  ├── AGENT_GUIDE.md  # AI agent development guide
  ├── adr/            # Architecture Decision Records
  │   ├── 0001-foodstate-identity-is-path.md
  │   └── 0002-fdc-as-evidence-not-identity.md
  └── sources/        # Source-specific documentation
      └── FDC_FOUNDATION_IMPORT.md

generated/             # Auto-generated content
  └── code.md         # Generated code documentation

Root configuration:
├── package.json      # Root package.json with Turbo scripts
├── turbo.json        # Turbo monorepo configuration
├── pnpm-workspace.yaml # PNPM workspace definition
├── tsconfig.base.json # Shared TypeScript configuration
├── etl/              # ETL pipeline and build automation
└── CONTRIBUTING.md   # Contribution guidelines
```

### Key architectural decisions:

- **Workspace packages**: Shared types flow from `packages/shared` → `packages/api-contract` → frontend
- **Data pipeline**: `data/ontology/` (source) → `data/ontology/compiled/` (intermediate) → `etl/dist/database/` (final)
- **Type safety**: Full TypeScript coverage with tRPC providing end-to-end type safety
- **Build system**: Turbo for monorepo orchestration, Vite for frontend, tsx for backend
- **Database**: SQLite with migrations and FTS (Full-Text Search) support
- **UI**: React + Tailwind + React Flow for graph visualization

---

## Scripts

At repo root:

- `pnpm dev` — run API + Web together (Turbo pipeline)
- `pnpm dev:api` / `pnpm dev:web` — run individually
- `pnpm db:build` — compile ontology → `etl/dist/database/graph.dev.sqlite`
- `pnpm db:open` — open the current DB in `sqlite3`
- `pnpm lint` / `pnpm typecheck` — standard hygiene

> If you prefer not to use Turbo, you can run `pnpm -C apps/api dev` and `pnpm -C apps/web dev` in separate terminals.

---

## Environment

The API looks for a SQLite DB path:

- **Env var:** `DB_PATH`
- **Default (if unset):** `<process.cwd()>/etl/dist/database/graph.dev.sqlite`

Because `apps/api` runs from its own working directory, we recommend setting an explicit path.

Create `apps/api/.env`:

```env
# API server
PORT=3000

# Point to the compiled DB at repo root
DB_PATH=../../etl/dist/database/graph.dev.sqlite
```

(Alternatively, keep the default and compile into `apps/api/etl/dist/database/…`.)

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
