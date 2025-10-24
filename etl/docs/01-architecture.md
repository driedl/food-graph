# ETL Architecture

## Overview

The ETL pipeline is designed as a modular, stage-based system that processes raw ontology data and external evidence sources into a comprehensive food knowledge graph. The architecture emphasizes determinism, observability, and composability.

## Core Design Principles

### 1. Stage-Based Processing
Each stage has a single responsibility with clear inputs and outputs:
- **Inputs**: Specific file types and data formats
- **Outputs**: Processed artifacts and reports
- **Contracts**: Validation rules for stage outputs

### 2. Deterministic Execution
- Identical inputs always produce identical outputs
- Byte-for-byte reproducibility across runs
- No random or time-dependent behavior

### 3. Observable Operations
- Rich logging at each stage
- JSON reports for programmatic analysis
- Lint findings and validation results
- Performance metrics and timing

### 4. Recoverable Processing
- Any stage can be re-run independently
- Resume capability from any stage
- Partial processing support
- Error isolation and recovery

### 5. Composable Design
- Easy to add new stages
- Minimal coupling between stages
- Clear interfaces and contracts
- Modular validation and testing

## Pipeline Architecture

### Stage Flow
```
Stage 0: Validation → Stage 1: NCBI → Stage A: Transforms → Stage B: Substrates
    ↓                      ↓                ↓                    ↓
Stage C: Derived → Stage D: Families → Stage E: Canonical → Stage F: SQLite → Stage G: Evidence
```

### Data Dependencies
```
Raw Ontology Data
       ↓
   Stage 0 (Validation)
       ↓
   Stage 1 (NCBI Integration)
       ↓
   Stage A (Transform Normalization)
       ↓
   Stage B (Substrate Materialization)
       ↓
   Stage C (Derived Food Ingestion)
       ↓
   Stage D (Family Templatization)
       ↓
   Stage E (Canonicalization)
       ↓
   Stage F (SQLite Database)
       ↓
   Stage G (Evidence Loading)
       ↓
   Final Database
```

## Stage Architecture

### Input/Output Pattern
Each stage follows a consistent pattern:

```python
def run(in_dir: Path, build_dir: Path, verbose: bool = False) -> Tuple[int, Dict[str, Any]]:
    """Stage X: Description"""
    
    # 1. Validate inputs
    # 2. Process data
    # 3. Generate outputs
    # 4. Validate outputs
    # 5. Return statistics
    
    return 0, {
        "duration_ms": duration,
        "records_processed": count,
        "errors": error_count
    }
```

### Contract Validation
Each stage has a contract that defines:
- Required output artifacts
- Minimum data requirements
- Schema validation rules
- Performance expectations

### Error Handling
- Graceful error handling with detailed messages
- Partial processing support
- Error reporting and logging
- Recovery strategies

## Evidence System Architecture

### 3-Tier Evidence Mapping
The evidence system uses a sophisticated 3-tier approach:

#### Tier 1: Taxon Resolution
- NCBI database integration
- Taxonomic verification
- Food name resolution
- Confidence scoring

#### Tier 2: TPT Construction
- Part applicability filtering
- Transform chain construction
- High-confidence processing
- Bypass Tier 3 when possible

#### Tier 3: Full Curation
- Low-confidence case processing
- Overlay system for modifications
- Manual curation support
- Proposal generation

### Evidence Loading (Stage G)
Stage G loads processed evidence data into the database:

1. **Evidence Mappings**: Food ID to TPT mappings
2. **Nutrient Data**: Individual nutrient measurements
3. **Rollup Computation**: Aggregated nutrient profiles
4. **Validation**: Referential integrity checks

## Database Architecture

### Core Tables
- **`nodes`**: Primary entity table (taxa, parts, transforms)
- **`edges`**: Relationship table with typed edges
- **`tpt_nodes`**: Transformed product table
- **`nutrients`**: Canonical nutrient definitions
- **`nutrient_row`**: Evidence data with provenance
- **`evidence_mapping`**: Food ID to TPT mappings
- **`nutrient_profile_rollup`**: Pre-computed profiles

### Relationships
```
taxa --[parent]--> taxa
parts --[parent]--> parts
transforms --[applies_to]--> parts
tpt_nodes --[uses]--> taxa
tpt_nodes --[uses]--> parts
tpt_nodes --[uses]--> transforms
nutrient_row --[references]--> tpt_nodes
nutrient_row --[references]--> nutrients
```

### Indexes
- Primary keys on all tables
- Foreign key indexes for relationships
- Full-text search indexes
- Composite indexes for common queries

## Configuration Management

### Build Configuration
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

### Stage Configuration
Each stage can have its own configuration:
- Input validation rules
- Processing parameters
- Output requirements
- Performance thresholds

## Performance Architecture

### Memory Management
- Streaming processing for large datasets
- Memory-efficient data structures
- Garbage collection optimization
- Memory usage monitoring

### Processing Optimization
- Batch processing where possible
- Parallel processing for independent operations
- Caching of frequently accessed data
- Database query optimization

### Scalability Design
- Horizontal scaling through stage isolation
- Vertical scaling through resource optimization
- Database partitioning strategies
- Index optimization

## Testing Architecture

### Unit Testing
- Individual stage testing
- Mock data and dependencies
- Isolated test environments
- Comprehensive coverage

### Integration Testing
- End-to-end pipeline testing
- Contract validation testing
- Performance testing
- Error scenario testing

### Contract Testing
- Output validation
- Schema compliance
- Performance requirements
- Data quality metrics

## Monitoring and Observability

### Logging
- Structured logging with JSON format
- Log levels (DEBUG, INFO, WARN, ERROR)
- Contextual information
- Performance metrics

### Metrics
- Processing time per stage
- Memory usage tracking
- Error rate monitoring
- Data quality metrics

### Reporting
- JSON reports for programmatic analysis
- Human-readable summaries
- Error reports and diagnostics
- Performance analysis

## Error Handling Architecture

### Error Types
- **Validation Errors**: Input data format issues
- **Processing Errors**: Runtime processing failures
- **Database Errors**: Database operation failures
- **System Errors**: Resource or environment issues

### Error Recovery
- Graceful degradation
- Partial processing support
- Resume capabilities
- Rollback strategies

### Error Reporting
- Detailed error messages
- Context information
- Suggested fixes
- Error aggregation and analysis

## Future Architecture Considerations

### Scalability
- Distributed processing
- Microservices architecture
- Event-driven processing
- Cloud-native deployment

### Performance
- Advanced caching strategies
- Database optimization
- Parallel processing
- Real-time processing

### Maintainability
- Modular design
- Clear interfaces
- Comprehensive testing
- Documentation standards