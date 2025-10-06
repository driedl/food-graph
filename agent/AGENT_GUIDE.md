# Agent Guide — Food Graph Project

> A comprehensive guide for AI agents working with the taxonomy-first nutrition graph codebase.

## 🎯 Project Overview

**Food Graph** is a monorepo for building a biological taxonomy-driven food & nutrition knowledge base. Identity is structural: **(Taxon + Part + Transform chain)**. Nutrient values are **evidence** that "fills" the graph.

**Vision:** Stable food identities based on biology + processing, not brittle name matching. Evidence can evolve without breaking canonical IDs.

### Key Principles

- **Identity is structural**: FoodState = Taxon + Part + ordered Transforms
- **Git-first ontology**: Human-authored, version-controlled, validated
- **Evidence over assertion**: Numbers come from provenance-tracked evidence
- **Compute on-demand**: FoodState paths are computed, not stored (for now)

## 🏗️ Architecture

### Core Entities

1. **Taxon** — Biological lineage (Life → Kingdom → ... → Species)
   - Example: `tx:plantae:poaceae:oryza:sativa` (Rice)
2. **Part** — Anatomical/edible parts (fruit, milk, muscle, grain)
   - Example: `part:milk`, `part:fruit`, `part:muscle`
3. **Transform** — Processes with parameters (cook, mill, ferment, cure)
   - Example: `tf:cook{method=boil,fat_added=false}`
4. **FoodState** — Identity-bearing path (not yet materialized in DB)
   - Example: `fs://plantae/poaceae/oryza/sativa/part:grain/tf:mill{refinement=whole}/tf:cook{method=boil}`
5. **Attribute** — Metadata with roles (identity_param, covariate, facet)

### Current Implementation Status

**✅ Implemented:**

- Taxonomy with 200+ taxa across plantae, animalia, fungi
- Parts system with 40+ parts and hierarchical applicability rules
- 29 transform families with param schemas
- FTS5 full-text search for taxa
- FoodState computation (on-demand via API)
- Documentation system (`.tx.md` files with YAML frontmatter)

**🔄 In Progress:**

- Taxon+part search nodes (see doc 14_TAXON_PART_SEARCH_PROPOSAL.md)
- Evidence model and nutrient data integration

**📋 Planned:**

- FoodState materialization in database
- Evidence tables with provenance
- Mixture DAG evaluation
- Hierarchical nutrient rollups

## 📁 Repository Structure

```
food-graph/
├── apps/
│   ├── api/              # Fastify + tRPC backend
│   └── web/              # React + Vite frontend
├── packages/
│   ├── shared/           # Shared types and FoodState logic
│   ├── config/           # Environment and path configuration
│   └── api-contract/     # API type definitions
├── etl/                  # ETL pipeline (Python)
│   └── graph/             # Python ETL framework
│       └── stages/       # Pipeline stages
├── data/
│   ├── ontology/         # Source of truth (Git)
│   │   ├── taxa/         # **/*.tx.md files with frontmatter
│   │   ├── parts.json
│   │   ├── transforms.json
│   │   ├── attributes.json
│   │   ├── nutrients.json
│   │   ├── animal_cuts/  # Hierarchical animal part defs
│   │   └── rules/        # Applicability rules (JSONL)
│   └── sources/          # External data (FDC, etc.)
├── docs/                 # Architecture & design docs
└── scripts/              # Utility scripts
```

## 🔧 Build Pipeline (ETL)

The ETL pipeline transforms Git-authored ontology data into a queryable SQLite database.

### Pipeline Steps

```bash
pnpm etl:run
```

**Runs:**

1. **Validate** — Schema checks, parent existence, acyclicity
2. **Compile Taxa** — Extract frontmatter from `.tx.md` → `taxa.jsonl`
3. **Compile Docs** — Extract markdown content → `docs.jsonl`
4. **Build Database** — Load all data into SQLite with FTS
5. **Verify** — Integrity checks and search tests
6. **Doc Report** — Coverage analysis

**Output:** `etl/build/database/graph.dev.sqlite`

### Ontology File Formats

**Taxa** (`.tx.md` with YAML frontmatter):

```markdown
---
id: tx:plantae:rosaceae:malus:domestica
rank: species
latin_name: Malus domestica
display_name: Apple
aliases: ['apple', 'apples']
tags: ['foundation']
---

Culinary notes, nutrition patterns, variability...
```

**Rules** (`rules/*.jsonl`):

```json
{"part":"part:milk","applies_to":["tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus"]}
{"transform":"tf:ferment","applies_to":[{"taxon_prefix":"tx:animalia:...","parts":["part:milk"]}]}
```

## 🗄️ Database Schema

### Taxonomy Tables

- **`nodes`** — Taxon hierarchy (id, name, slug, rank, parent_id)
- **`synonyms`** — Alternative names for taxa
- **`node_attributes`** — Key-value attributes on nodes (reserved)
- **`attr_def`** — Attribute registry (kind: numeric|boolean|categorical, role)
- **`attr_enum`** — Enum values for categorical attributes

### Documentation Tables

- **`taxon_doc`** — Markdown docs per taxon (summary, description_md, updated_at, checksum)

### Parts & Transforms

- **`part_def`** — Part registry (id, name, kind, notes, parent_id)
- **`part_synonym`** — Part aliases
- **`has_part`** — Materialized taxon ↔ part relationships
- **`transform_def`** — Transform registry (id, name, identity, schema_json, ordering)
- **`transform_applicability`** — Allowed transforms per taxon+part

### Search

- **`taxa_fts`** — FTS5 virtual table for taxa (name, synonyms, taxon_rank)
- **`tp_fts`** — FTS5 virtual table for taxon+part nodes (name, synonyms, taxon_rank, kind)

### Key Indexes

- `idx_nodes_parent` — Fast child queries
- `idx_nodes_slug_parent` — Unique slug per parent
- `idx_taxon_doc_taxon_id` — Doc lookups

## 🔌 API Endpoints (tRPC)

All endpoints are under `/trpc/`:

### Health

- `health` → `{ ok: true }`

### Taxonomy

- `taxonomy.getRoot` → Root node
- `taxonomy.getNode({ id })` → Single node
- `taxonomy.getChildren({ id, orderBy?, offset?, limit? })` → Children list
- `taxonomy.neighborhood({ id, childLimit, orderBy })` → Node + parent + siblings + children + counts
- `taxonomy.pathToRoot({ id })` → Lineage array from node to root
- `taxonomy.search({ q, rankFilter? })` → FTS5 search results
- `taxonomy.getPartsForTaxon({ id })` → Parts applicable to taxon (via lineage)
- `taxonomy.partTree({ id })` → Hierarchical part tree

### Documentation

- `docs.getByTaxon({ taxonId })` → Doc for taxon

### Search (Combined)

- `search.combined({ q, kinds?, limit? })` → Unified search (taxa + docs)
- `search.docs({ q, lang?, limit? })` → Doc-only search

### FoodState (Computation)

- `foodstate.compose({ taxonId, partId, transforms })` → Computes FoodState path with validation

## 📊 Ontology Reference

### ID Conventions

- **Taxa**: `tx:<path>` (e.g., `tx:plantae:poaceae:oryza:sativa`)
- **Parts**: `part:<slug>` (e.g., `part:fruit`, `part:milk`)
- **Transforms**: `tf:<slug>` (e.g., `tf:cook`, `tf:mill`)
- **Attributes**: `attr:<slug>` (e.g., `attr:salt_level`)
- **Nutrients**: `nutr:<slug>` (e.g., `nutr:protein_g`)

### Ranks

`root | domain | kingdom | phylum | class | order | family | genus | species | subspecies | cultivar | variety | breed | product | form`

### Transform Families (Examples)

- `tf:cook` — `{method: enum(raw|boil|steam|bake|roast|fry|broil), fat_added: boolean}`
- `tf:mill` — `{refinement: enum(whole|refined|pearled|00), oat_form?: enum(rolled|steel_cut)}`
- `tf:ferment` — `{starter: enum(yogurt_thermo|yogurt_meso|kefir|...), temp_C, time_h}`
- `tf:cure` — `{method: enum(dry|wet), salt_pct, sugar_pct, nitrite_ppm, time_d}`

See `data/ontology/transforms.json` for all 29 transforms.

### Attribute Roles

1. **identity_param** — Affects FoodState identity (e.g., `salt_level`, `fat_pct`)
2. **taxon_refinement** — Rare; internal taxonomy refinement
3. **covariate** — Influences evidence selection, not identity (e.g., `ripeness_bucket`, `region`)
4. **facet** — Discovery metadata only (e.g., `color`, `brand`)

## 🛠️ Quick Commands

### Database Access

```bash
# Interactive SQL REPL
pnpm sql:repl

# Run a single query (returns JSON)
pnpm sql "SELECT * FROM nodes LIMIT 3"

# Pipe SQL from stdin
echo 'SELECT count(*) c FROM nodes;' | pnpm sql --stdin

# Open SQLite shell
pnpm db:open
```

### Development

```bash
# Start API + Web (parallel)
pnpm dev

# Start API only
pnpm dev:api

# Start Web only
pnpm dev:web

# Full type check + lint + ETL build
pnpm check

# Build database from ontology
pnpm etl:run

# Run ETL validation only
pnpm etl:run --with-tests

# Run smoke tests
pnpm etl:run --with-tests

# List all tRPC routes
pnpm api:routes
```

### Debugging

```bash
# View ETL pipeline config
cat etl/graph/config.py

# Check database stats
pnpm sql "SELECT
  (SELECT COUNT(*) FROM nodes) as taxa,
  (SELECT COUNT(*) FROM synonyms) as synonyms,
  (SELECT COUNT(*) FROM taxon_doc) as docs,
  (SELECT COUNT(*) FROM has_part) as has_part_rows,
  (SELECT COUNT(*) FROM nodes_fts) as fts_entries;"

# View recent docs
pnpm sql "SELECT taxon_id, display_name, updated_at FROM taxon_doc ORDER BY updated_at DESC LIMIT 5;"
```

## 🔍 Common Queries

### Find Root Node

```sql
SELECT * FROM nodes WHERE parent_id IS NULL;
```

### Get Children of a Node

```sql
SELECT * FROM nodes WHERE parent_id = 'tx:plantae' ORDER BY name;
```

### Search Using FTS5

```sql
-- Search taxa
SELECT n.* FROM nodes n
JOIN taxa_fts fts ON taxa_fts.rowid = n.rowid
WHERE taxa_fts MATCH 'apple'
ORDER BY bm25(taxa_fts) ASC
LIMIT 10;

-- Search taxon+part combinations
SELECT tp.* FROM taxon_part_nodes tp
JOIN tp_fts fts ON tp_fts.rowid = tp.rowid
WHERE tp_fts MATCH 'milk'
ORDER BY bm25(tp_fts) ASC
LIMIT 10;
```

### Get Path to Root (Lineage)

```sql
WITH RECURSIVE lineage(id,name,slug,rank,parent_id,depth) AS (
  SELECT id,name,slug,rank,parent_id,0 FROM nodes WHERE id = 'tx:plantae:rosaceae:malus:domestica'
  UNION ALL
  SELECT n.id,n.name,n.slug,n.rank,n.parent_id,depth+1 FROM nodes n
  JOIN lineage l ON n.id = l.parent_id
)
SELECT id,name,slug,rank,parent_id FROM lineage ORDER BY depth DESC;
```

### Get Parts for a Taxon (with inheritance)

```sql
WITH RECURSIVE lineage(id) AS (
  SELECT id FROM nodes WHERE id = 'tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus'
  UNION ALL
  SELECT n.parent_id FROM nodes n JOIN lineage l ON n.id = l.id WHERE n.parent_id IS NOT NULL
)
SELECT DISTINCT p.id, p.name, p.kind
FROM has_part hp
JOIN part_def p ON p.id = hp.part_id
WHERE hp.taxon_id IN (SELECT id FROM lineage)
ORDER BY p.kind, p.name;
```

### Search Documentation

```sql
-- Documentation is not currently searchable via FTS
-- Use LIKE queries for basic text search in taxon_doc table
SELECT taxon_id, display_name, summary
FROM taxon_doc
WHERE summary LIKE '%fermented%' OR description_md LIKE '%cultured%'
LIMIT 10;
```

## 🧪 FoodState Examples

### Computing a FoodState Path

```typescript
// Via API endpoint
const result = await trpc.foodstate.compose.query({
  taxonId: 'tx:plantae:poaceae:oryza:sativa',
  partId: 'part:grain',
  transforms: [
    { id: 'tf:mill', params: { refinement: 'whole' } },
    { id: 'tf:cook', params: { method: 'boil', fat_added: false } }
  ]
})

// Returns:
{
  id: 'fs://plantae/poaceae/oryza/sativa/part:grain/tf:mill{refinement=whole}/tf:cook{fat_added=false,method=boil}',
  errors: [],
  normalized: { taxonId, partId, transforms }
}
```

### Identity Rules

- Only **identity-bearing** transforms appear in path (`identity: true` in transform_def)
- Transforms are ordered by `ordering` field (e.g., mill before cook)
- Params are canonicalized (alpha-sorted, booleans as `true`/`false`, numbers without trailing zeros)

## 📚 Documentation Index

Located in `docs/`:

1. **00_VISION.md** — Aspirational goals and principles
2. **01_ARCHITECTURE.md** — Core entities and edges
3. **02_ONTOLOGY_KIT.md** — Authoring formats and compile process
4. **03_ID_CONVENTIONS.md** — ID shapes and stability policy
5. **04_ATTRIBUTES.md** — Attribute roles and promotion policy
6. **05_TRANSFORMS.md** — Transform families and math
7. **06_EVIDENCE_MODEL.md** — Evidence types and rollups (planned)
8. **07_ROADMAP.md** — Implementation phases
9. **08_PRIORS_EMBEDDINGS.md** — Statistical models (planned)
10. **09_CLASSIFICATIONS_AND_OVERLAYS.md** — Regulatory/market taxonomies (planned)
11. **10_QA_GUARDS.md** — Quality checks (planned)
12. **11_STORAGE_AND_ARTIFACTS.md** — File layout and build outputs
13. **12_RULES_APPLICABILITY.md** — Part and transform applicability system
14. **13_MONOREPO_OPTIMIZATION.md** — Technical debt analysis
15. **14_TAXON_PART_SEARCH_PROPOSAL.md** — Taxon+part search design

### ADRs (Architecture Decision Records)

- **0001-foodstate-identity-is-path.md** — Why paths, not UUIDs
- **0002-fdc-as-evidence-not-identity.md** — Evidence vs identity separation

## 🐛 Troubleshooting

### Database Not Found

```bash
# Rebuild from ontology
pnpm etl:run

# Check if file exists
ls -lh etl/build/database/graph.dev.sqlite
```

### FTS Search Not Working

```bash
# Verify FTS tables exist
pnpm sql "SELECT COUNT(*) FROM taxa_fts;"
pnpm sql "SELECT COUNT(*) FROM tp_fts;"

# Test search
pnpm sql "SELECT * FROM taxa_fts WHERE taxa_fts MATCH 'apple' LIMIT 1;"
pnpm sql "SELECT * FROM tp_fts WHERE tp_fts MATCH 'milk' LIMIT 1;"
```

### API Returns 404

```bash
# List all routes
pnpm api:routes

# Check if API is running
curl http://localhost:3000/trpc/health
```

### Stale Data in Reports

```bash
# Clean and rebuild
pnpm etl:clean
pnpm etl:run
```

## 🎯 Development Tips

1. **Type Safety**: Import types from `@nutrition/shared` and `@nutrition/api-contract`
2. **Path Resolution**: Use `@nutrition/config` for all file paths (never hardcode)
3. **FTS5 Search**: Supports phrase matching, boolean operators, prefix matching with `*`
4. **Performance**: Database uses WAL mode; read queries are concurrent
5. **Validation**: Run `pnpm etl:run --with-tests` before committing ontology changes
6. **Hot Reload**: API uses `tsx watch`; web uses Vite HMR
7. **Transform Order**: Transforms execute in `ordering` sequence (lower = earlier)
8. **Part Inheritance**: Parts cascade down taxonomy via `has_part` materialization

## 🔐 Configuration

Environment variables (via `@nutrition/config`):

- `PORT` — API server port (default: 3000)
- `DB_PATH` — SQLite database path (default: `etl/build/database/graph.dev.sqlite`)
- `NODE_ENV` — Environment: development|test|production

## 📦 Package Reference

- **`@nutrition/api`** — Fastify + tRPC backend (apps/api)
- **`@nutrition/web`** — React + Vite frontend (apps/web)
- **`@nutrition/shared`** — FoodState logic, shared types (packages/shared)
- **`@nutrition/config`** — Zod-validated env config, paths (packages/config)
- **`@nutrition/api-contract`** — Type-only API exports (packages/api-contract)

---

**For more details, see the full documentation in `/docs/` or start with `docs/INDEX.md`.**
