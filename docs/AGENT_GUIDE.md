# Agent Guide

This guide helps AI agents understand how to work with the nutrition-graph codebase effectively.

## Quick Commands

### Database Access
```bash
# Interactive SQL REPL
pnpm sql:repl

# Run a single query (returns JSON)
pnpm sql "SELECT * FROM nodes LIMIT 3"

# Pipe SQL from stdin
echo 'SELECT count(*) c FROM nodes;' | pnpm sql --stdin
```

### API Routes
```bash
# List all available TRPC routes
pnpm api:routes
```

### Development
```bash
# Start both API and web app
pnpm dev

# Type checking and linting
pnpm check

# Build database from ontology
pnpm db:build
```

## Database Schema

### Core Tables
- `nodes`: Main taxonomy nodes (id, name, slug, rank, parent_id)
- `synonyms`: Alternative names for nodes
- `node_attributes`: Key-value attributes on nodes
- `attr_def`: Attribute definitions (kind: numeric|boolean|categorical)
- `nodes_fts`: Full-text search index (FTS5)

### Key Queries

```sql
-- Find root nodes
SELECT * FROM nodes WHERE parent_id IS NULL;

-- Get children of a node
SELECT * FROM nodes WHERE parent_id = 'node-id';

-- Search using FTS5
SELECT n.* FROM nodes n 
JOIN nodes_fts fts ON n.rowid = fts.rowid 
WHERE nodes_fts MATCH 'search terms';

-- Get path to root (recursive)
WITH RECURSIVE lineage(id,name,slug,rank,parent_id,depth) AS (
  SELECT id,name,slug,rank,parent_id,0 FROM nodes WHERE id = ?
  UNION ALL
  SELECT n.id,n.name,n.slug,n.rank,n.parent_id,depth+1 FROM nodes n
  JOIN lineage l ON n.id = l.parent_id
)
SELECT id,name,slug,rank,parent_id FROM lineage ORDER BY depth DESC;
```

## API Endpoints

All endpoints are under `/trpc/`:

- `health`: API health check
- `taxonomy.getRoot`: Get root taxonomy node
- `taxonomy.getChildren`: Get children of a node
- `taxonomy.getNode`: Get a specific node
- `taxonomy.pathToRoot`: Get path from node to root
- `taxonomy.search`: Search nodes using FTS5

## Configuration

Environment variables (via `@nutrition/config`):
- `PORT`: API server port (default: 3000)
- `DB_PATH`: SQLite database path
- `NODE_ENV`: development|test|production

## Package Structure

- `@nutrition/api`: Fastify + TRPC API server
- `@nutrition/web`: React + Vite web app
- `@nutrition/api-contract`: Type-only exports for API
- `@nutrition/config`: Zod-validated environment config
- `@nutrition/shared`: Shared utilities

## Migrations

Database migrations are in `apps/api/migrations/`:
- `0001_init.sql`: Core schema (nodes, synonyms, attributes)
- `0002_nodes_fts.sql`: FTS5 search index

Run migrations automatically on API startup.

## Development Tips

1. **Type Safety**: Use `@nutrition/api-contract` for type-only imports
2. **Search**: FTS5 supports phrase matching and boolean operators
3. **Performance**: React Flow is lazy-loaded to reduce bundle size
4. **Styling**: Uses CSS variables + Tailwind for theming
5. **Bundling**: Vendor chunks are split for better caching
