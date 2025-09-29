# ETL Pipeline

The **Food Graph ETL Pipeline** is a unified build system that compiles ontology data into a searchable SQLite database. This package consolidates all data processing, validation, and compilation steps into a streamlined, maintainable pipeline.

## Quick Start

```bash
# Build the complete database
pnpm etl:build

# Run validation only
pnpm etl:validate

# Clean build artifacts
pnpm etl:clean
```

## Pipeline Overview

The ETL pipeline processes food taxonomy data through 4 main steps:

```
📁 Raw Ontology Data → 🔍 Validate → 📦 Compile → 🗄️ Database → ✅ Verify
```

### Step 1: Validate

- **Script**: `python/validate_taxa.py`
- **Purpose**: Validates taxonomic data integrity and consistency
- **Input**: `data/ontology/taxa/` (raw NDJSON files)
- **Checks**: ID consistency, parent relationships, banned terms, file alignment

### Step 2: Compile Taxa

- **Script**: `python/compile_taxa.py`
- **Purpose**: Compiles taxonomic hierarchy into structured JSONL
- **Input**: `data/ontology/taxa/`
- **Output**: `data/ontology/compiled/taxa/taxa.jsonl`
- **Also copies**: `attributes.json`, `parts.json`, `nutrients.json`, `transforms.json`

### Step 3: Compile Documentation

- **Script**: `python/compile_docs.py`
- **Purpose**: Processes taxonomic documentation from `.tx.md` files
- **Input**: `data/ontology/taxa/docs/` (markdown files with YAML front-matter)
- **Output**: `data/ontology/compiled/docs.jsonl`

### Step 4: Build Database

- **Script**: `python/compile.py`
- **Purpose**: Compiles ontology data into SQLite database with full-text search
- **Input**: `data/ontology/compiled/`
- **Output**: `data/builds/graph.dev.sqlite`

## Pipeline Architecture

### TypeScript Orchestration

The pipeline is orchestrated by TypeScript code in `src/`:

- **`src/build.ts`** - Main pipeline runner with step execution and progress reporting
- **`src/pipeline/`** - Pipeline configuration and step definitions
  - **`config.ts`** - Pipeline step definitions and paths
  - **`runner.ts`** - Pipeline execution engine with error handling
  - **`types.ts`** - TypeScript interfaces for pipeline data
  - **`steps/verify.ts`** - Database verification and smoke tests

### Python Scripts

Core data processing is handled by Python scripts in `python/`:

- **`validate_taxa.py`** - Taxonomic data validation
- **`compile_taxa.py`** - Taxonomic data compilation
- **`compile_docs.py`** - Documentation compilation
- **`compile.py`** - Database compilation with FTS creation

## Database Schema

The pipeline creates a complete SQLite database with:

### Core Tables

- **`nodes`** - Taxonomic hierarchy (id, name, slug, rank, parent_id)
- **`synonyms`** - Alternative names for taxa
- **`node_attributes`** - Key-value attributes on nodes
- **`attr_def`** - Attribute definitions (numeric|boolean|categorical)

### Full-Text Search

- **`nodes_fts`** - FTS5 virtual table for fast search
  - Indexes: `name`, `synonyms`, `taxon_rank`
  - Triggers: Automatic synchronization with nodes/synonyms changes

### Extended Schema

- **`taxon_doc`** - Taxonomic documentation
- **`part_def`** - Food part definitions
- **`has_part`** - Taxon-part relationships
- **`transform_def`** - Processing transform definitions
- **`transform_applicability`** - Transform-taxon-part applicability rules

## Usage

### From Root Directory

```bash
# Full pipeline
pnpm etl:build
```

### From ETL Directory

```bash
# Direct pipeline execution
pnpm build:pipeline

# Individual steps
pnpm validate
pnpm clean
```

### Programmatic Usage

```typescript
import { PipelineRunner } from './src/pipeline/runner.js';

const runner = new PipelineRunner();
const report = await runner.run(['validate', 'compile-taxa']);
```

## Configuration

Pipeline configuration is defined in `src/pipeline/config.ts`:

```typescript
export const pipelineConfig: PipelineConfig = {
  steps: [
    { id: 'validate', command: 'python3', args: [...] },
    { id: 'compile-taxa', command: 'python3', args: [...] },
    // ...
  ],
  inputs: {
    ontologyRoot: 'data/ontology',
    compiledDir: 'data/ontology/compiled',
    buildsDir: 'data/builds'
  },
  outputs: {
    taxaJsonl: 'data/ontology/compiled/taxa/taxa.jsonl',
    docsJsonl: 'data/ontology/compiled/docs.jsonl',
    database: 'data/builds/graph.dev.sqlite'
  }
}
```

## Error Handling

The pipeline includes comprehensive error handling:

- **Step-by-step validation** - Each step validates its input before proceeding
- **Early exit on failure** - Pipeline stops immediately if any step fails
- **Clear error messages** - Detailed error reporting with suggestions
- **Rollback on failure** - Failed builds don't leave partial state

## Performance

Typical build times:

- **Full pipeline**: ~200ms
- **Validation only**: ~50ms
- **Database build**: ~100ms

The pipeline is optimized for fast iteration during development.

## Troubleshooting

### Common Issues

**"No taxa found under data/ontology/taxa"**

- Ensure you're running from the repo root
- Check that ontology data exists in `data/ontology/taxa/`

**"FTS search returns no results"**

- Verify database was built successfully
- Check that FTS table has entries: `SELECT COUNT(*) FROM nodes_fts`
- Rebuild database: `pnpm etl:build`

**"Pipeline step failed"**

- Check Python dependencies are installed
- Verify file permissions on ontology data
- Run individual steps to isolate the issue

### Debug Mode

Add `--verbose` flag to Python scripts for detailed output:

```bash
python3 python/compile.py --verbose
```

## Development

### Adding New Steps

1. Create Python script in `python/`
2. Add step definition to `src/pipeline/config.ts`
3. Update pipeline runner if needed
4. Test with `pnpm build:pipeline`

### Modifying Database Schema

1. Update schema in `python/compile.py`
2. Update FTS table structure if needed
3. Update API router queries if search changes
4. Run full pipeline test
