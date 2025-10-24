# Nutrition Evidence System

## Overview

The Nutrition Evidence System provides a comprehensive pipeline for mapping external nutrition data sources (FDC, Canadian NF, Euro Food, etc.) to our canonical food ontology. The system uses a 3-tier mapping approach with resume support for batch-by-batch curation workflow.

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
- Stores both original FDC values and canonical converted values
- Flags unmapped nutrients for manual curation

### Incremental Processing (Resume Support)

- Skips already processed foods to enable batch-by-batch curation
- Appends new results to existing JSONL files
- Supports multi-source data integration
- JSONL acts as intermediate "staging" layer before DB import

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

### Input Sources

- **FDC Foundation**: USDA FoodData Central foundation foods
- **Canadian NF**: Canadian Nutrient File
- **Euro Food**: European food composition databases
- **Future**: Additional international sources

### Processing Pipeline

1. **Load Source Data**: Parse external nutrition databases
2. **Tier 1 Resolution**: Resolve taxa using NCBI verification
3. **Tier 2 Construction**: Build TPT combinations with part filtering
4. **Tier 3 Curation**: Handle complex cases requiring human review
5. **Nutrient Mapping**: Map to canonical INFOODS format
6. **Output Generation**: Create JSONL files for staging

## File Structure

### Evidence Directory Layout

```
data/evidence/
├── fdc-foundation/
│   ├── evidence_mappings.jsonl    # Food → TPT mappings
│   ├── nutrient_data.jsonl        # Nutrient data per food
│   ├── detailed_results.jsonl     # Full mapping details
│   └── overlay_summary.json       # Ontology proposals
├── canadian-nf/
│   └── [similar structure]
└── euro-food/
    └── [similar structure]
```

### Proposals Directory

```
data/ontology/_proposals/
├── unmapped_nutrients.jsonl       # Unmapped nutrient proposals
├── unmapped_nutrients_report.md   # Human-readable report
└── [other ontology proposals]
```

## Key Features

### Resume Support

The system supports incremental processing:

```bash
# Process first batch
pnpm evidence:map --limit 50

# Review results and proposals
# Edit data/ontology/_proposals/unmapped_nutrients.jsonl

# Process next batch (automatically skips processed foods)
pnpm evidence:map --limit 50
```

### Comprehensive Nutrient Mapping

- **86 FDC nutrients** mapped (vs previous 9)
- **Unit conversions** applied automatically
- **Dual storage** of original and converted values
- **Unmapped proposals** for manual curation

### Multi-Source Support

- **Source tracking** in all data
- **Confidence scoring** per source
- **Conflict resolution** in final profiles
- **Provenance** maintained throughout

## Usage

### Basic Evidence Mapping

```python
from etl.evidence.evidence_mapper import EvidenceMapper

# Initialize mapper
mapper = EvidenceMapper(
    graph_db_path=Path("etl/build/database/graph.dev.sqlite"),
    ncbi_db_path=Path("etl/build/database/ncbi.sqlite"),
    overlay_dir=Path("data/ontology/_overlay")
)

# Map FDC evidence
results = mapper.map_fdc_evidence(
    fdc_dir=Path("data/sources/fdc"),
    output_dir=Path("data/evidence/fdc-foundation"),
    limit=50,  # Process 50 foods
    min_confidence=0.7,
    resume=True  # Skip already processed foods
)
```

### Batch Processing Workflow

1. **Process initial batch**:
   ```bash
   pnpm evidence:map --limit 50
   ```

2. **Review results and proposals**:
   - Check `data/evidence/fdc-foundation/evidence_mappings.jsonl`
   - Review `data/ontology/_proposals/unmapped_nutrients_report.md`

3. **Approve/merge proposals**:
   - Update `nutrients.json` with new mappings
   - Merge ontology proposals

4. **Process next batch**:
   ```bash
   pnpm evidence:map --limit 50  # Resume mode automatically enabled
   ```

## Output Files

### Evidence Mappings (`evidence_mappings.jsonl`)

```json
{
  "food_id": "fdc:12345",
  "food_name": "Apple, raw",
  "taxon_id": "tx:p:malus:domestica",
  "part_id": "fruit",
  "transforms": ["raw"],
  "confidence": 0.95,
  "disposition": "mapped",
  "reason": "High confidence TPT construction",
  "overlay_applied": false
}
```

### Nutrient Data (`nutrient_data.jsonl`)

```json
{
  "food_id": "12345",
  "nutrient_id": "ENERC_KCAL",
  "amount": 52.0,
  "unit": "kcal",
  "original_amount": 52.0,
  "original_unit": "KCAL",
  "original_nutrient_id": "208",
  "conversion_factor": 1.0,
  "source": "fdc_foundation",
  "confidence": 0.9,
  "nutrient_name": "Energy (kcal)",
  "nutrient_class": "proximate"
}
```

### Unmapped Nutrient Proposals (`unmapped_nutrients.jsonl`)

```json
{
  "fdc_id": "9999",
  "fdc_name": "Unknown Nutrient",
  "fdc_unit": "G",
  "occurrence_count": 15,
  "sample_food_ids": ["food1", "food2", "food3"],
  "suggested_action": "map",
  "confidence": "high",
  "notes": "Found in 15 foods. Most common name: Unknown Nutrient, unit: G"
}
```

## Configuration

### Nutrient Mapping

The system uses `data/ontology/nutrients.json` as the source of truth for all nutrient mappings. This file contains:

- Canonical INFOODS nutrient definitions
- FDC candidate IDs for each nutrient
- Unit conversion factors
- Confidence levels and metadata

### Resume Mode

Resume mode is enabled by default and:

- Reads existing `evidence_mappings.jsonl` to find processed foods
- Skips foods that have already been processed
- Appends new results to existing files
- Enables incremental batch processing

### Unmapped Nutrient Handling

Unmapped nutrients are automatically:

- Collected during processing
- Grouped by FDC ID and occurrence frequency
- Assigned suggested actions based on frequency:
  - `map`: High occurrence (≥10 foods)
  - `review`: Medium occurrence (3-9 foods)  
  - `ignore`: Low occurrence (<3 foods)
- Saved to `data/ontology/_proposals/unmapped_nutrients.jsonl`

## Verification

Run the verification script to check mapping consistency:

```bash
npx tsx scripts/verify-nutrient-mapping.ts
```

This will:

- Compare `nutrients.json` with `fdc_to_infoods.jsonl`
- Verify all FDC candidates have valid mappings
- Check unit conversion factors are consistent
- Report any issues or gaps

## Testing

Run the test suite:

```bash
cd etl
python -m pytest tests/test_nutrient_mapping.py -v
```

Tests cover:

- FDC-to-INFOODS mapping completeness
- Unit conversions
- Unmapped nutrient detection
- Original/converted value storage
- Resume functionality

## Performance

- **High-confidence cases**: Bypass expensive Tier 3 processing
- **Resume support**: Avoids re-processing completed foods
- **Batch processing**: Enables iterative curation workflow
- **Comprehensive mapping**: All 86 FDC nutrients mapped (vs 9 previously)

## Future Enhancements

- Multi-source data integration (Canadian NF, Euro Food, etc.)
- Automated proposal merging
- Enhanced confidence scoring
- Real-time mapping validation
- Advanced conflict resolution strategies

## Related Documentation

- [3-Tier Evidence Mapping System](../etl/evidence/README.md) - Detailed technical documentation
- [Architecture Overview](01_ARCHITECTURE.md) - Core graph model
- [ETL Pipeline](../etl/docs/00-overview.md) - Build system overview
- [Curation Workflow](../etl/docs/08-curation-workflow.md) - Data curation process