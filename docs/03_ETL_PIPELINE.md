# ETL Pipeline

## Overview

The ETL (Extract, Transform, Load) pipeline processes raw ontology data and external evidence sources into a comprehensive food knowledge graph. The pipeline is designed for speed, reliability, and incremental processing.

## Pipeline Architecture

### Stage Overview

The ETL pipeline consists of 8 stages (0-G) that process data sequentially:

```
Raw Data → Stage 0 → Stage 1 → Stage A → Stage B → Stage C → Stage D → Stage E → Stage F → Stage G
   ↓         ↓        ↓        ↓        ↓        ↓        ↓        ↓        ↓        ↓
Ontology → Validate → NCBI → Transforms → Substrates → Derived → Families → Canonical → SQLite → Evidence
```

### Data Flow

```
data/ontology/ → ETL Pipeline → build/database/ → API
     ↓                ↓              ↓            ↓
JSONL Files → Processing → SQLite DB → Queries
```

## Stage Details

### Stage 0: Validation and Preprocessing
**Input**: Raw ontology JSONL files  
**Output**: Validated and normalized data  
**Duration**: ~2 seconds

- Validates taxon ID formats
- Checks part hierarchy consistency
- Verifies transform definitions
- Generates validation reports

### Stage 1: NCBI Integration
**Input**: Validated taxon data  
**Output**: NCBI-verified taxa with lineage data  
**Duration**: ~3 seconds

- Loads NCBI taxonomy database
- Verifies taxon IDs against NCBI
- Adds lineage and parent relationships
- Flags unverified taxa

### Stage A: Transform Normalization
**Input**: Raw transform definitions  
**Output**: Canonical transform catalog  
**Duration**: ~1 second

- Normalizes transform parameters
- Adds order and class metadata
- Validates identity parameters
- Generates transform catalog

### Stage B: Substrate Materialization
**Input**: Parts and applicability rules  
**Output**: Taxon-Part substrate combinations  
**Duration**: ~2 seconds

- Applies part applicability rules
- Generates substrate combinations
- Validates taxon-part relationships
- Creates substrate catalog

### Stage C: Derived Food Ingestion
**Input**: Curated derived food definitions  
**Output**: Validated derived food catalog  
**Duration**: ~1 second

- Loads curated derived foods
- Validates against substrates
- Strips non-identity transforms
- Creates derived food catalog

### Stage D: Family Templatization
**Input**: Family definitions and allowlists  
**Output**: Generated TPT families  
**Duration**: ~2 seconds

- Applies family templates
- Generates TPT combinations
- Validates family rules
- Creates family catalog

### Stage E: Canonicalization and ID Generation
**Input**: TPT definitions and parameters  
**Output**: Canonical TPTs with deterministic IDs  
**Duration**: ~3 seconds

- Sorts transforms by order
- Buckets parameters
- Computes identity hashes
- Generates canonical TPT IDs

### Stage F: SQLite Database Creation
**Input**: All processed data  
**Output**: SQLite database with full-text search  
**Duration**: ~5 seconds

- Creates database schema
- Loads all entity data
- Builds full-text search indexes
- Validates referential integrity

### Stage G: Evidence Loading and Rollup
**Input**: Evidence JSONL files  
**Output**: Populated evidence tables with rollups  
**Duration**: ~2 seconds

- Loads evidence mappings
- Loads nutrient data
- Computes nutrient profile rollups
- Validates referential integrity

## Configuration

### Build Configuration
The pipeline uses `build_config.json` for configuration:

```json
{
  "in_dir": "data/ontology",
  "build_dir": "build",
  "verbose": true,
  "with_tests": true,
  "stages": ["0", "1", "A", "B", "C", "D", "E", "F", "G"]
}
```

### Environment Variables
- `NUTRITION_GRAPH_VERBOSE`: Enable verbose logging
- `NUTRITION_GRAPH_BUILD_DIR`: Override build directory
- `NUTRITION_GRAPH_IN_DIR`: Override input directory

## Running the Pipeline

### Full Pipeline
```bash
# Run all stages
python -m etl.graph.cli run build

# Run with verbose output
python -m etl.graph.cli run build --verbose
```

### Individual Stages
```bash
# Run specific stage
python -m etl.graph.cli run F

# Run stage range
python -m etl.graph.cli run ABC
```

### Resume from Stage
```bash
# Resume from stage E
python -m etl.graph.cli run EFG
```

## Performance Characteristics

### Build Times
- **Full Pipeline**: ~20 seconds
- **Incremental**: ~5 seconds
- **Stage G Only**: ~2 seconds

### Memory Usage
- **Peak Memory**: ~200MB
- **Typical Memory**: ~100MB
- **Stage G Memory**: ~50MB

### Scalability
- **Taxa**: 100K+ taxa
- **TPTs**: 1M+ TPT combinations
- **Evidence**: 10M+ nutrient measurements

## Error Handling

### Validation Errors
- Schema validation failures
- Referential integrity violations
- Data consistency errors
- Format validation errors

### Recovery Strategies
- Detailed error reporting
- Partial processing support
- Resume from last valid stage
- Rollback on critical errors

### Monitoring
- Progress tracking with ETA
- Error rate monitoring
- Performance metrics
- Quality score reporting

## Testing

### Unit Tests
```bash
# Run all tests
python -m pytest etl/tests/

# Run specific test
python -m pytest etl/tests/test_stage_f.py
```

### Integration Tests
```bash
# Run ETL pipeline tests
python -m etl.graph.cli test build
```

### Contract Validation
Each stage has output contracts that are validated:
- Required artifacts present
- Minimum row counts
- Schema validation
- Referential integrity

## Debugging

### Verbose Output
```bash
# Enable verbose logging
python -m etl.graph.cli run build --verbose
```

### Stage-specific Debugging
```bash
# Run single stage with verbose output
python -m etl.graph.cli run F --verbose
```

### Artifact Inspection
```bash
# Inspect stage outputs
ls build/tmp/
ls build/graph/
ls build/database/
```

## Maintenance

### Regular Tasks
- Update NCBI taxonomy database
- Refresh external data sources
- Validate data consistency
- Monitor performance metrics

### Troubleshooting
- Check build logs for errors
- Validate input data quality
- Verify database integrity
- Test individual stages

## Future Enhancements

### Planned Features
- Parallel stage execution
- Incremental processing
- Real-time updates
- Advanced caching

### Performance Improvements
- Database optimization
- Memory usage reduction
- Faster validation
- Improved error handling
