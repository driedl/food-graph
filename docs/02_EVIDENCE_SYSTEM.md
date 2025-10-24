# Evidence System

## Overview

The Evidence System provides a comprehensive pipeline for mapping external nutrition data sources (FDC, Canadian NF, Euro Food, etc.) to our canonical food ontology. The system uses a 3-tier mapping approach with resume support for batch-by-batch curation workflow.

## Architecture

### 3-Tier Evidence Mapping System

**Tier 1: Taxon Resolution**
- Uses NCBI database for taxonomic verification
- Resolves food names to canonical taxon IDs
- Skips processed food mixtures (hummus, etc.)

**Tier 2: TPT Construction**
- Constructs Taxon-Part-Transform combinations
- Uses lineage-based part filtering
- High-confidence results bypass Tier 3

**Tier 3: Full Curation**
- Processes low-confidence cases
- Can propose new parts/transforms via overlay system
- Only runs when needed for efficiency

### Comprehensive Nutrient Mapping

- Maps all 86 FDC nutrient IDs to canonical INFOODS format
- Uses `nutrients.json` as authoritative source
- Applies unit conversions using `unit_factor_from_fdc`
- Stores both original and converted values
- Flags unmapped nutrients for manual curation

## Data Flow

```
External Sources → Evidence Mapper → JSONL Files → Stage G → Graph DB → API
     ↓                    ↓              ↓            ↓          ↓         ↓
FDC/Canadian/Euro → 3-Tier Mapping → Staging → Load+Rollup → SQLite → Queries
```

### Stage G: Evidence Loading and Rollup

Stage G is the final ETL stage that:

1. Loads evidence JSONL files into the database
2. Computes pre-aggregated nutrient profile rollups
3. Applies source quality weighting

This stage only runs if `data/evidence/` directory exists with processed sources.

## Evidence Loading Process

### Input Files
- `evidence_mappings.jsonl` - Food ID to TPT mappings
- `nutrient_data.jsonl` - Nutrient values with conversions
- `unmapped_nutrients.jsonl` - Nutrients requiring manual curation

### Database Tables
- `evidence_mapping` - Food ID to TPT mappings with confidence scores
- `nutrient_row` - Individual nutrient measurements with provenance
- `nutrient_profile_rollup` - Pre-computed aggregated profiles

### Validation
- TPT ID validation against `tpt_nodes` table
- Nutrient ID validation against `nutrients` table
- Referential integrity checks
- Schema validation for all input data

## Rollup Computation

### Algorithm
1. Group nutrient data by `(tpt_id, nutrient_id)`
2. Apply source quality weights: `source_weight * row_confidence`
3. Compute weighted median (robust to outliers)
4. Store statistics: min, max, count, confidence

### Source Quality Tiers
- **Tier 1** (Weight 1.0): FDC Foundation, Canadian NF, Euro Food
- **Tier 2** (Weight 0.9): FDC SR Legacy
- **Tier 3** (Weight 0.6): FDC Branded foods
- **Default** (Weight 0.5): Unknown sources

### Configuration
Source quality weights are defined in `data/ontology/source_quality.json`:

```json
{
  "source_types": {
    "fdc": {
      "name": "USDA FoodData Central",
      "base_weight": 1.0,
      "method_weights": {
        "analytical": 1.0,
        "calculated": 0.8,
        "imputed": 0.5
      }
    }
  }
}
```

## Resume Support

The evidence mapper supports incremental processing:

- Tracks processed food IDs in `processed_foods.jsonl`
- Skips already processed foods on subsequent runs
- Enables batch-by-batch curation workflow
- Supports partial processing for debugging

### Usage
```bash
# Process first batch (10% of FDC foods)
python -m etl.evidence.evidence_mapper --limit 1000

# Process next batch (resume from where left off)
python -m etl.evidence.evidence_mapper --resume

# Process all remaining foods
python -m etl.evidence.evidence_mapper --resume --limit 0
```

## Unmapped Nutrient Curation

### Automatic Detection
- Identifies FDC nutrients not in canonical ontology
- Generates human-readable reports
- Creates JSONL proposals for manual review

### Curation Workflow
1. Review `unmapped_nutrients_report.md`
2. Edit `unmapped_nutrients_proposals.jsonl`
3. Merge approved proposals into `nutrients.json`
4. Re-run evidence mapping

### Proposal Format
```json
{
  "fdc_id": "1313",
  "fdc_name": "Calcium, Ca",
  "unit": "mg",
  "proposed_infoods_id": "CA",
  "proposed_unit": "mg",
  "conversion_factor": 1.0,
  "confidence": 0.9,
  "notes": "Direct mapping to INFOODS Calcium"
}
```

## API Integration

### Nutrient Profile Queries
```typescript
// Get aggregated nutrient profile for a TPT
const profile = await api.nutrition.getNutrientProfile.query({
  tptId: "tpt:tx:a:salmo:salar:part:fillet:SMOKED:abc123"
});

// Get detailed evidence for a TPT
const evidence = await api.nutrition.getNutrientEvidence.query({
  tptId: "tpt:tx:a:salmo:salar:part:fillet:SMOKED:abc123"
});
```

### Search Integration
- TPT search includes nutrient profile metadata
- Filter by nutrient content ranges
- Sort by nutritional density

## Performance Characteristics

### Processing Speed
- **Evidence Mapping**: ~100 foods/second
- **Stage G Loading**: ~1000 records/second
- **Rollup Computation**: ~100 TPTs/second

### Memory Usage
- **Evidence Mapper**: ~500MB for FDC Foundation
- **Stage G**: ~100MB for typical datasets
- **API Queries**: <10MB per request

### Scalability
- Supports 100K+ foods per source
- Handles 1M+ nutrient measurements
- Processes multiple sources in parallel

## Error Handling

### Validation Errors
- Missing required fields
- Invalid TPT references
- Malformed JSON data
- Schema violations

### Recovery Strategies
- Skip invalid records with warnings
- Generate detailed error reports
- Support partial processing
- Enable resume from last valid state

### Monitoring
- Progress tracking with ETA
- Error rate monitoring
- Performance metrics
- Quality score reporting

## Future Enhancements

### Planned Features
- Multi-source conflict resolution
- Machine learning quality scoring
- Real-time evidence updates
- Advanced curation tools

### Data Sources
- Canadian Nutrient File integration
- European food databases
- Branded food databases
- Scientific literature integration
