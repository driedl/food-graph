# ETL2 Agent Guide

This guide helps AI agents understand and work with the ETL2 system effectively.

## Quick Start

### Package Management
- **Use `pnpm`** for all package management (not npm/yarn)
- Install dependencies: `pnpm install`
- Run scripts: `pnpm <script-name>`

### Database Queries
- **Ad-hoc SQL queries**: `pnpm sql "SELECT * FROM nodes LIMIT 5"`
- This connects to the ETL2 database and runs queries directly
- Useful for debugging data issues and exploring the schema
- **Database browser**: `pnpm db:open` opens sqlite3 CLI on the ETL2 database

## ETL2 ↔ API Relationship

### Architecture
- **ETL2** compiles ontology data into a SQLite database
- **API** copies the ETL2 database to its own location and reads from there
- **ETL2 database**: `etl2/build/database/graph.dev.sqlite`
- **API database**: `apps/api/database/graph.dev.sqlite` (auto-copied from ETL2)

### Workflow
1. **ETL2 stages** (0→F) process raw ontology data
2. **Stage F** creates the final SQLite database with all tables
3. **API startup** checks if its database exists and is up-to-date
4. **Auto-copy** happens if database is missing or version mismatch detected
5. **API** reads from its own copy of the database

### Key Tables
- `nodes` - taxonomic hierarchy
- `part_def` - food parts (muscle, leaf, etc.)
- `has_part` - taxon-part relationships
- `tpt_nodes` - Taxon+Part+Transform combinations
- `transform_def` - transform definitions
- `tpt_identity_steps` - exploded transform steps
- `taxon_ancestors` - lineage closure table

## Debugging Commands

### ETL2 Pipeline
```bash
# Run specific stage
python3 -m mise run F --verbose

# Run full pipeline
python3 -m mise run build --verbose

# Check stage verification
python3 -c "from mise.contracts.engine import verify; verify('stage_f', Path('etl2'), Path('etl2/build'), verbose=True)"
```

### Database Inspection
```bash
# List all tables
pnpm sql ".tables"

# Check table structure
pnpm sql ".schema transform_def"

# Count rows in key tables
pnpm sql "SELECT 'nodes' as table_name, COUNT(*) as count FROM nodes UNION ALL SELECT 'transform_def', COUNT(*) FROM transform_def;"

# Check new tables exist
pnpm sql "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('transform_def', 'tpt_identity_steps', 'taxon_ancestors');"
```

### API Testing
```bash
# Start API (auto-copies ETL2 database if needed)
pnpm --filter api dev

# Test API endpoints
curl http://localhost:3000/api/health
curl "http://localhost:3000/api/taxonomy/getRoot"
curl "http://localhost:3000/api/entities/get?id=tx:plantae"
```

## Common Issues & Solutions

### Stage F Verification Fails
- **Problem**: Contract expects wrong database filename
- **Check**: `etl2/mise/stages/stage_f/contract.yml` should have `database/graph.dev.sqlite`
- **Fix**: Update contract path to match actual database location

### API Can't Find Database
- **Problem**: API can't find ETL2 database to copy from
- **Check**: `ETL2_DB_PATH` environment variable points to ETL2 database
- **Fix**: Set `ETL2_DB_PATH=etl2/build/database/graph.dev.sqlite` or let it use default

### Missing Tables Error
- **Problem**: API expects tables that don't exist
- **Check**: Database has `transform_def`, `tpt_identity_steps`, `taxon_ancestors`
- **Fix**: Re-run Stage F to populate new tables

### Port Already in Use
- **Problem**: API can't start on port 3000
- **Fix**: Kill existing process or use different port
```bash
lsof -ti:3000 | xargs kill -9
```

## File Locations

- **ETL2 source**: `etl2/mise/stages/`
- **Database output**: `etl2/build/database/graph.dev.sqlite`
- **API source**: `apps/api/src/`
- **Config**: `packages/config/src/index.ts` (uses `ETL2_DB_PATH` env var)
- **Reports**: `etl2/build/report/`

## Schema Changes

When adding new tables to ETL2:
1. Update `etl2/mise/stages/stage_f/sqlite_pack.py` DDL
2. Add population logic in `build_sqlite()` function
3. Update `etl2/mise/stages/stage_f/contract.yml` validators
4. Update `apps/api/src/db.ts` required tables list
5. Test with `python3 -m mise run F --verbose`
