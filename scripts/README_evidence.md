# Evidence Mapping Scripts

This directory contains scripts for running the 3-tier evidence mapping system.

## Available Scripts

### Package.json Scripts

- `pnpm evidence:map` - Run evidence mapping with default settings
- `pnpm evidence:map:limit` - Run evidence mapping with limit of 100 foods
- `pnpm evidence:map:test` - Run evidence mapping with limit of 10 foods and lower confidence threshold
- `pnpm evidence:map:full` - Run evidence mapping with full command line (no wrapper)

### Custom Parameters

You can pass any parameters to the evidence mapping system:

```bash
# Custom limit
pnpm evidence:map --limit 50

# Custom confidence threshold
pnpm evidence:map --min-confidence 0.8

# Custom model
pnpm evidence:map --model gpt-5

# Custom output directory
pnpm evidence:map --output data/evidence/my-custom-run

# Verbose output
pnpm evidence:map --verbose

# Multiple parameters
pnpm evidence:map --limit 25 --min-confidence 0.6 --model gpt-5-mini --verbose
```

### Direct Usage

You can also run the evidence mapper directly:

```bash
cd etl
python3 -m evidence.evidence_mapper \
    --graph-db ./build/database/graph.dev.sqlite \
    --ncbi-db ./build/database/ncbi.sqlite \
    --fdc-dir ../data/sources/fdc \
    --output ../data/evidence/fdc-foundation-3tier \
    --limit 100 \
    --min-confidence 0.7
```

## Parameters

- `--graph-db` - Path to graph database (default: etl/build/database/graph.dev.sqlite)
- `--ncbi-db` - Path to NCBI database (default: etl/build/database/ncbi.sqlite)
- `--fdc-dir` - Path to FDC data directory (default: data/sources/fdc)
- `--output` - Output directory for results (default: data/evidence/fdc-foundation-3tier)
- `--overlay-dir` - Overlay directory for temporary modifications (default: data/ontology/_overlay)
- `--model` - LLM model to use (default: gpt-5-mini)
- `--limit` - Limit number of foods to process (default: 0 = no limit)
- `--min-confidence` - Minimum confidence threshold (default: 0.7)
- `--verbose` - Enable verbose output

## Prerequisites

1. **NCBI Database**: Must be built first
   ```bash
   python etl/graph/external/ncbi_loader.py --output etl/build/database/ncbi.sqlite
   ```

2. **Graph Database**: Must be built first
   ```bash
   pnpm etl:run
   ```

3. **Environment Variables**: Set `OPENAI_API_KEY`
   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```

## Output Files

The evidence mapping system creates several output files:

- `evidence_mappings.jsonl` - Main evidence mappings
- `nutrient_data.jsonl` - Nutrient data for mapped foods
- `detailed_results.jsonl` - Detailed results with all tiers
- `overlay_summary.json` - Summary of overlay modifications

## Examples

### Quick Test Run
```bash
pnpm evidence:map:test
```

### Production Run with Limit
```bash
pnpm evidence:map:limit
```

### Full Production Run
```bash
pnpm evidence:map
```

### Custom Run
```bash
pnpm evidence:map --limit 200 --min-confidence 0.8 --model gpt-5 --verbose
```
