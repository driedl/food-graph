# ADR-0003: Nutrient Mapping Strategy

## Status
Accepted

## Context

The food graph system needs to integrate external nutrition data sources (FDC, Canadian NF, Euro Food, etc.) with our canonical food ontology. These external sources use different nutrient ID schemes and units than our canonical INFOODS-based system.

Key challenges:
- FDC uses SR Legacy IDs (e.g., `1008` for Energy)
- Our system uses INFOODS IDs (e.g., `ENERC_KCAL` for Energy)
- Different units across sources (kcal vs kJ, mg vs μg)
- Need to preserve original values for reprocessing
- Unmapped nutrients require manual curation

## Decision

We will implement a comprehensive nutrient mapping system that:

### 1. Canonical Nutrient Ontology
- Use `nutrients.json` as the authoritative source of truth
- Store INFOODS IDs, units, and conversion factors
- Include FDC candidate IDs for mapping
- Support unit conversions with `unit_factor_from_fdc`

### 2. Comprehensive Mapping
- Map all 86+ FDC nutrient IDs to canonical format
- Apply unit conversions automatically
- Store both original and converted values
- Track conversion factors and provenance

### 3. Unmapped Nutrient Handling
- Flag unmapped nutrients for manual curation
- Generate human-readable reports
- Create JSONL proposals for review
- Support incremental curation workflow

### 4. Data Storage Strategy
- Store original values in `original_amount`, `original_unit`, `original_nutrient_id`
- Store converted values in `amount`, `unit`, `nutrient_id`
- Track conversion factors for reprocessing
- Maintain source attribution

## Implementation

### Database Schema
```sql
CREATE TABLE nutrient_row (
  id TEXT PRIMARY KEY,
  food_id TEXT NOT NULL,
  nutrient_id TEXT NOT NULL,           -- Canonical INFOODS ID
  amount REAL NOT NULL,                -- Converted amount
  unit TEXT NOT NULL,                  -- Canonical unit
  original_amount REAL NOT NULL,       -- Original amount
  original_unit TEXT NOT NULL,         -- Original unit
  original_nutrient_id TEXT NOT NULL,  -- Original FDC ID
  conversion_factor REAL NOT NULL,     -- Conversion factor applied
  source TEXT NOT NULL,
  confidence REAL NOT NULL,
  notes TEXT,
  created_at TEXT,
  nutrient_name TEXT,                  -- Human-readable name
  nutrient_class TEXT,                 -- Nutrient class
  tpt_id TEXT REFERENCES tpt_nodes(id)
);
```

### Mapping Process
1. Load canonical nutrient definitions from `nutrients.json`
2. Create FDC-to-INFOODS mapping using `fdc_to_infoods.jsonl`
3. Apply unit conversions using stored conversion factors
4. Store both original and converted values
5. Flag unmapped nutrients for curation

### Curation Workflow
1. Generate unmapped nutrient reports
2. Create JSONL proposals for manual review
3. Merge approved proposals into `nutrients.json`
4. Re-run evidence mapping with updated mappings

## Consequences

### Positive
- **Comprehensive Coverage**: All FDC nutrients mapped to canonical format
- **Data Integrity**: Original values preserved for reprocessing
- **Flexibility**: Easy to change canonical scheme and regenerate
- **Curation Support**: Clear workflow for handling unmapped nutrients
- **Provenance**: Full tracking of data transformations

### Negative
- **Complexity**: More complex data model and processing
- **Storage**: Additional storage for original values
- **Maintenance**: Need to maintain mapping files and conversion factors
- **Curation Overhead**: Manual work required for unmapped nutrients

### Risks
- **Mapping Errors**: Incorrect mappings could propagate through system
- **Unit Conversion Errors**: Mathematical errors in unit conversions
- **Data Loss**: Risk of losing original data during transformations
- **Curation Bottleneck**: Manual curation could become bottleneck

## Mitigation Strategies

### Data Quality
- Comprehensive validation of mappings
- Unit conversion verification
- Regular auditing of mapped data
- Automated testing of conversion logic

### Curation Efficiency
- Clear reporting of unmapped nutrients
- Batch processing for curation
- Automated proposal generation
- Integration with existing curation tools

### Error Handling
- Detailed error reporting
- Rollback capabilities
- Data validation at each step
- Comprehensive logging

## Alternatives Considered

### 1. Store Only Converted Values
**Rejected**: Would lose ability to reprocess with different canonical scheme

### 2. Store Only Original Values
**Rejected**: Would require conversion on every query, impacting performance

### 3. Separate Mapping Service
**Rejected**: Adds complexity without clear benefits

### 4. Manual Mapping Only
**Rejected**: Would not scale to 86+ nutrients and multiple sources

## Implementation Timeline

### Phase 1: Core Mapping (Completed)
- [x] Create `nutrient_mapper.py` with comprehensive FDC mapping
- [x] Update `NutrientRow` schema with original/converted fields
- [x] Integrate mapping into evidence mapper pipeline
- [x] Create unmapped nutrient collection system

### Phase 2: Curation Tools (Completed)
- [x] Generate human-readable reports
- [x] Create JSONL proposal format
- [x] Implement resume support for batch processing
- [x] Add validation and verification scripts

### Phase 3: Integration (Completed)
- [x] Update database schema
- [x] Integrate with Stage G evidence loading
- [x] Add rollup computation with source weighting
- [x] Update API endpoints for nutrient queries

## Monitoring and Success Metrics

### Data Quality Metrics
- Mapping coverage: >95% of FDC nutrients mapped
- Conversion accuracy: 100% verified conversions
- Data completeness: All required fields populated
- Validation errors: <1% of records

### Performance Metrics
- Mapping speed: >1000 nutrients/second
- Storage efficiency: <20% overhead for original values
- Query performance: <100ms for nutrient queries
- Curation throughput: >100 proposals/hour

### User Experience Metrics
- Curation time: <5 minutes per unmapped nutrient
- Error rate: <0.1% user-facing errors
- Documentation clarity: >90% user satisfaction
- Support requests: <10% related to mapping issues

## Future Considerations

### Additional Sources
- Canadian Nutrient File integration
- European food databases
- Branded food databases
- Scientific literature integration

### Advanced Features
- Machine learning for mapping suggestions
- Automated unit conversion validation
- Real-time mapping updates
- Advanced curation tools

### Performance Optimization
- Caching of mapping results
- Parallel processing of large datasets
- Incremental mapping updates
- Database query optimization
