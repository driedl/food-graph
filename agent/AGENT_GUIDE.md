# Agent Guide — Food Graph Project

> A comprehensive guide for AI agents working with the taxonomy-first nutrition graph codebase.

## 🎯 Project Overview

**Food Graph** is a monorepo for building a biological taxonomy-driven food & nutrition knowledge base. The system uses a **TPT (Taxon-Part-Transform)** model where food identity is structural: **(Taxon + Part + Transform chain)**. Nutrient values are **evidence** that "fills" the graph.

**Vision:** Stable food identities based on biology + processing, not brittle name matching. Evidence can evolve without breaking canonical IDs.

### Core Concepts

- **Taxa (T)**: Biological sources (e.g., `tx:p:malus:domestica` for apple)
- **Parts (P)**: Anatomical components (e.g., `part:fruit`, `part:muscle`)
- **Transforms (TF)**: Processing operations (e.g., `tf:cook`, `tf:ferment`)
- **TPT**: Transformed products (e.g., `tpt:tx:p:malus:domestica:part:fruit:FRESH:abc123`)
- **Evidence**: Nutrition data mapped to TPTs via 3-tier system

## 🏗️ System Architecture

### ETL Pipeline (8 Stages: 0, 1, A-G)

The ETL pipeline compiles Git-authored ontology data into a queryable SQLite database:

```bash
# Full pipeline
pnpm etl:run

# Individual stages
pnpm etl:run --stage 0    # Validation & preprocessing
pnpm etl:run --stage 1    # NCBI integration
pnpm etl:run --stage A    # Transform normalization
pnpm etl:run --stage B    # Substrate materialization
pnpm etl:run --stage C    # Derived food ingestion
pnpm etl:run --stage D    # Family templatization
pnpm etl:run --stage E    # Canonicalization & IDs
pnpm etl:run --stage F    # SQLite database creation
pnpm etl:run --stage G    # Evidence loading & rollups
```

**Output**: `etl/build/database/graph.dev.sqlite`

### Evidence System (3-Tier Mapping)

The system maps external nutrition data (FDC, etc.) to canonical TPTs:

1. **Tier 1**: Taxon-only resolution with NCBI verification
2. **Tier 2**: TPT construction with lineage-based part filtering
3. **Tier 3**: Full curation with overlay system for complex cases

```bash
# Map evidence from FDC
pnpm evidence:map --limit 100
pnpm evidence:map:test --limit 10 --min-confidence 0.5
pnpm evidence:map:full  # Full FDC processing
```

### Database Schema

**Core Tables**:
- `nodes` — Taxa, parts, transforms with hierarchical relationships
- `edges` — Typed relationships between entities
- `tpt_nodes` — Transformed products with identity hashes
- `nutrients` — Canonical nutrient definitions (INFOODS format)
- `nutrient_row` — Evidence data with original + converted values
- `evidence_mapping` — Food ID to TPT mapping with confidence scores
- `nutrient_profile_rollup` — Pre-computed nutrient profiles

## 📁 Repository Structure

```
food-graph/
├── apps/
│   ├── api/              # Fastify + tRPC backend
│   └── web/              # React + Vite frontend
├── packages/
│   ├── shared/           # Shared types and FoodState logic
│   ├── config/           # Environment configuration
│   └── api-contract/     # API type definitions
├── etl/                  # Python ETL pipeline
│   ├── graph/            # Stage-based ETL framework
│   └── evidence/         # 3-tier evidence mapping system
├── data/
│   ├── ontology/         # Source of truth (Git)
│   │   ├── taxa/         # **/*.tx.md files with frontmatter
│   │   ├── parts.json
│   │   ├── transforms.json
│   │   ├── nutrients.json
│   │   └── rules/        # Applicability rules (JSONL)
│   └── sources/          # External data (FDC, etc.)
├── scripts/              # Utility scripts
└── docs/                 # Architecture & design docs
```

## 🔧 Essential Commands

### Development Workflow

```bash
# Start API + Web (parallel)
pnpm dev

# Start individually
pnpm dev:api
pnpm dev:web

# Build everything
pnpm build

# Type checking and linting
pnpm check
```

### ETL Pipeline

```bash
# Install Python dependencies
pnpm etl:install

# Run full pipeline
pnpm etl:run

# Run with tests/validation
pnpm etl:run --with-tests

# Clean build artifacts
pnpm etl:clean

# Show pipeline help
pnpm etl:plan
```

### Evidence System

```bash
# Map evidence (incremental)
pnpm evidence:map --limit 50

# Test mapping with low confidence
pnpm evidence:map:test --limit 10 --min-confidence 0.5

# Full FDC processing
pnpm evidence:map:full

# Generate evidence profiles
pnpm evidence:profiles

# Validate evidence data
pnpm evidence:validate
```

### Database Access

```bash
# Interactive SQL REPL
pnpm sql:repl

# Run single query (returns JSON)
pnpm sql "SELECT * FROM nodes LIMIT 3"

# Pipe SQL from stdin
echo 'SELECT count(*) c FROM nodes;' | pnpm sql --stdin

# Open SQLite shell
pnpm db:open
```

### Utility Scripts

```bash
# List all tRPC routes
pnpm api:routes

# Sync database
pnpm sync-db

# Stop all services
pnpm stop

# Aggregation tools
pnpm ag:etl    # ETL aggregation
pnpm ag:api    # API aggregation
```

## 🗄️ Database Querying

### Common Query Patterns

**Find root node**:
```sql
SELECT * FROM nodes WHERE parent_id IS NULL;
```

**Get children of a node**:
```sql
SELECT * FROM nodes WHERE parent_id = 'tx:p' ORDER BY name;
```

**Search using FTS5**:
```sql
-- Search taxa
SELECT n.* FROM nodes n
JOIN taxa_fts fts ON taxa_fts.rowid = n.rowid
WHERE taxa_fts MATCH 'apple'
ORDER BY bm25(taxa_fts) ASC
LIMIT 10;
```

**Get lineage to root**:
```sql
WITH RECURSIVE lineage(id,name,slug,rank,parent_id,depth) AS (
  SELECT id,name,slug,rank,parent_id,0 FROM nodes WHERE id = 'tx:p:malus:domestica'
  UNION ALL
  SELECT n.id,n.name,n.slug,n.rank,n.parent_id,depth+1 FROM nodes n
  JOIN lineage l ON n.id = l.parent_id
)
SELECT id,name,slug,rank,parent_id FROM lineage ORDER BY depth DESC;
```

**Query TPT nodes**:
```sql
-- Find TPTs for a specific taxon
SELECT * FROM tpt_nodes WHERE taxon_id = 'tx:p:malus:domestica';

-- Find TPTs with specific part
SELECT * FROM tpt_nodes WHERE part_id = 'part:fruit';
```

**Query evidence data**:
```sql
-- Get nutrient data for a food
SELECT nr.*, n.name as nutrient_name, n.unit as canonical_unit
FROM nutrient_row nr
JOIN nutrients n ON n.id = nr.nutrient_id
WHERE nr.food_id = 'fdc:12345';

-- Get evidence mapping
SELECT em.*, tpt.taxon_id, tpt.part_id, tpt.family
FROM evidence_mapping em
JOIN tpt_nodes tpt ON tpt.id = em.tpt_id
WHERE em.food_id = 'fdc:12345';
```

**Query nutrient profiles**:
```sql
-- Get rollup profile for a TPT
SELECT * FROM nutrient_profile_rollup WHERE tpt_id = 'tpt:...';

-- Find foods with high protein
SELECT tpt_id, protein_g FROM nutrient_profile_rollup 
WHERE protein_g > 20 ORDER BY protein_g DESC;
```

## 🔌 API Endpoints (tRPC)

All endpoints are under `/trpc/`:

### Core Routers

- **`health`** → `{ ok: true }`
- **`taxonomy.*`** — Taxon hierarchy navigation
- **`search.*`** — Full-text search across entities
- **`entities.*`** — Generic entity retrieval
- **`browse.*`** — Hierarchical browsing
- **`taxa.*`** — Taxon-specific operations
- **`tp.*`** — Taxon-Part combinations
- **`tpt.*`** — Transformed products
- **`tptAdvanced.*`** — Advanced TPT operations
- **`facets.*`** — Metadata and flags
- **`docs.*`** — Documentation retrieval
- **`foodstate.*`** — FoodState computation
- **`evidence.*`** — Evidence and nutrition data
- **`meta.*`** — System metadata

### Key Endpoints

**Taxonomy**:
- `taxonomy.getRoot` → Root node
- `taxonomy.getNode({ id })` → Single node
- `taxonomy.getChildren({ id, orderBy?, offset?, limit? })` → Children list
- `taxonomy.neighborhood({ id, childLimit, orderBy })` → Node + context
- `taxonomy.search({ q, rankFilter? })` → FTS5 search results

**Search**:
- `search.combined({ q, kinds?, limit? })` → Unified search
- `search.docs({ q, lang?, limit? })` → Doc-only search

**TPT Operations**:
- `tpt.get({ id })` → Get TPT by ID
- `tpt.search({ q, filters? })` → Search TPTs
- `tptAdvanced.getNutrientProfile({ tptId })` → Get nutrition profile

**Evidence**:
- `evidence.getByFoodId({ foodId })` → Get evidence for FDC food
- `evidence.getNutrientData({ tptId, nutrientId? })` → Get nutrient data
- `evidence.search({ q, filters? })` → Search evidence

## 🧪 FoodState Examples

### Computing a FoodState Path

```typescript
// Via API endpoint
const result = await trpc.foodstate.compose.query({
  taxonId: 'tx:p:malus:domestica',
  partId: 'part:fruit',
  transforms: [
    { id: 'tf:mill', params: { refinement: 'whole' } },
    { id: 'tf:cook', params: { method: 'boil', fat_added: false } }
  ]
})

// Returns:
{
  id: 'fs://p/malus/domestica/part:fruit/tf:mill{refinement=whole}/tf:cook{fat_added=false,method=boil}',
  errors: [],
  normalized: { taxonId, partId, transforms }
}
```

## 📊 Evidence System Usage

### Mapping External Data

The evidence system maps external nutrition data to canonical TPTs:

```bash
# Process FDC data in batches
pnpm evidence:map --limit 100

# Review unmapped nutrients
cat data/ontology/_proposals/unmapped_nutrients_report.md

# Validate evidence data
pnpm evidence:validate
```

### Querying Evidence

```sql
-- Find evidence for a specific food
SELECT em.*, tpt.taxon_id, tpt.part_id, tpt.family
FROM evidence_mapping em
JOIN tpt_nodes tpt ON tpt.id = em.tpt_id
WHERE em.food_id = 'fdc:12345';

-- Get nutrient data with confidence scores
SELECT nr.nutrient_id, nr.amount, nr.unit, nr.confidence, n.name
FROM nutrient_row nr
JOIN nutrients n ON n.id = nr.nutrient_id
WHERE nr.food_id = 'fdc:12345'
ORDER BY nr.confidence DESC;
```

## 🐛 Troubleshooting

### Database Not Found
```bash
# Rebuild from ontology
pnpm etl:run

# Check if file exists
ls -lh etl/build/database/graph.dev.sqlite
```

### ETL Pipeline Issues
```bash
# Check stage-specific errors
pnpm etl:run --stage 0 --verbose

# Clean and rebuild
pnpm etl:clean
pnpm etl:run
```

### Evidence Mapping Issues
```bash
# Check evidence validation
pnpm evidence:validate

# Review unmapped nutrients
cat data/ontology/_proposals/unmapped_nutrients_report.md
```

### API Issues
```bash
# Check if API is running
curl http://localhost:3000/trpc/health

# List all routes
pnpm api:routes
```

## 🎯 Quick Reference

### Essential File Locations
- **Database**: `etl/build/database/graph.dev.sqlite`
- **Ontology**: `data/ontology/`
- **Evidence**: `data/evidence/`
- **ETL Code**: `etl/`
- **API Code**: `apps/api/`
- **Web UI**: `apps/web/`

### Key Environment Variables
- `DB_PATH` — SQLite database path
- `PORT` — API server port (default: 3000)
- `NODE_ENV` — Environment (development|test|production)

### Common Workflows

1. **Add new food**: Create taxon in `data/ontology/taxa/`, run ETL
2. **Map nutrition data**: Use evidence mapping system
3. **Query nutrition**: Use `evidence.*` API endpoints or direct SQL
4. **Debug ETL**: Run individual stages with `--verbose`
5. **Explore data**: Use `pnpm sql:repl` for interactive queries

## 📚 Documentation Index

For detailed information, see:
- **Architecture**: `docs/01_ARCHITECTURE.md`
- **Evidence System**: `docs/02_EVIDENCE_SYSTEM.md`
- **ETL Pipeline**: `docs/03_ETL_PIPELINE.md`
- **API Reference**: `docs/04_API_REFERENCE.md`
- **Development Guide**: `docs/05_DEVELOPMENT_GUIDE.md`
- **ETL Details**: `etl/docs/00-overview.md`
- **Evidence Details**: `etl/evidence/README.md`

---

**This guide provides everything needed to immediately start working with the Food Graph project. For specific implementation details, refer to the linked documentation.**