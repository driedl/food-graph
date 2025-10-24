# 3-Tier Evidence Mapping System

## Overview

The 3-Tier Evidence Mapping System provides a comprehensive pipeline for mapping food data from external sources (like FDC) to our canonical ontology. The system uses three tiers of processing to balance efficiency with accuracy:

- **Tier 1**: Taxon-only resolver with NCBI verification
- **Tier 2**: TPT constructor with lineage-based part filtering  
- **Tier 3**: Full curator with overlay system for complex cases

## Key Features

### Comprehensive Nutrient Mapping
- Maps all 86 FDC nutrient IDs to canonical INFOODS format
- Applies unit conversions using `unit_factor_from_fdc` from `nutrients.json`
- Stores both original FDC values and canonical converted values
- Flags unmapped nutrients for manual curation

### Incremental Processing (Resume Support)
- Skips already processed foods to enable batch-by-batch curation
- Appends new results to existing JSONL files
- Supports multi-source data integration (FDC, Canadian, Euro, etc.)

### Unmapped Nutrient Proposals
- Automatically flags unmapped nutrients for manual review
- Groups by occurrence frequency and suggests actions
- Generates human-readable reports for curation

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

## Architecture

### Tier 1: Taxon Resolution
- Uses NCBI database for taxonomic verification
- Resolves food names to canonical taxon IDs
- Skips processed food mixtures (hummus, etc.)

### Tier 2: TPT Construction
- Constructs Taxon-Part-Transform combinations
- Uses lineage-based part filtering
- High-confidence results bypass Tier 3

### Tier 3: Full Curation
- Processes low-confidence cases
- Can propose new parts/transforms via overlay system
- Only runs when needed for efficiency

### Nutrient Processing
- Comprehensive mapping using `nutrients.json`
- Unit conversions applied automatically
- Both original and converted values stored
- Unmapped nutrients flagged for curation

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