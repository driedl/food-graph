from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from .db_utils import get_db_connection, get_missing_tpt_ids, get_missing_nutrient_ids, log_validation_errors, create_evidence_stats, log_stats
from .jsonl_utils import read_jsonl_safe, validate_jsonl_schema

def load_evidence_to_db(
    evidence_base_dir: Path,
    graph_db_path: Path,
    verbose: bool = False
) -> Dict[str, int]:
    """Load all evidence JSONL files into graph database"""
    
    if not evidence_base_dir.exists():
        if verbose:
            print(f"  • Evidence directory {evidence_base_dir} does not exist")
        return create_evidence_stats()
    
    # Find all source directories
    source_dirs = [d for d in evidence_base_dir.iterdir() if d.is_dir()]
    
    if not source_dirs:
        if verbose:
            print(f"  • No source directories found in {evidence_base_dir}")
        return create_evidence_stats()
    
    if verbose:
        print(f"  • Found {len(source_dirs)} source directories")
    
    stats = create_evidence_stats()
    
    with get_db_connection(graph_db_path, verbose) as con:
        for source_dir in source_dirs:
            source_name = source_dir.name
            if verbose:
                print(f"  • Loading source: {source_name}")
            
            # Load evidence mappings
            mappings_file = source_dir / "evidence_mappings.jsonl"
            if mappings_file.exists():
                mappings_count, validation_errors = _load_evidence_mappings(con, mappings_file, source_name, verbose)
                stats['mappings_loaded'] += mappings_count
                stats['validation_errors'] += validation_errors
                if verbose:
                    print(f"    - Loaded {mappings_count} evidence mappings, {validation_errors} validation errors")
            else:
                if verbose:
                    print(f"    - No evidence_mappings.jsonl found")
            
            # Load nutrient data
            nutrients_file = source_dir / "nutrient_data.jsonl"
            if nutrients_file.exists():
                nutrient_rows_count, validation_errors = _load_nutrient_data(con, nutrients_file, source_name, verbose)
                stats['nutrient_rows_loaded'] += nutrient_rows_count
                stats['validation_errors'] += validation_errors
                if verbose:
                    print(f"    - Loaded {nutrient_rows_count} nutrient rows, {validation_errors} validation errors")
            else:
                if verbose:
                    print(f"    - No nutrient_data.jsonl found")
        
        stats['sources_loaded'] = len(source_dirs)
        con.commit()
    
    log_stats(stats, "Evidence Loading", verbose)
    return stats

def _load_evidence_mappings(con: sqlite3.Connection, mappings_file: Path, source_name: str, verbose: bool) -> Tuple[int, int]:
    """Load evidence mappings from JSONL file with validation"""
    
    # Clear existing mappings for this source
    con.execute("DELETE FROM evidence_mapping WHERE source = ?", (source_name,))
    
    mappings_count = 0
    validation_errors = 0
    
    # Read and validate data
    mappings_data = list(read_jsonl_safe(mappings_file, verbose))
    
    # Validate schema
    required_fields = ['food_id', 'taxon_id', 'part_id', 'transforms', 'confidence', 'disposition']
    schema_errors = validate_jsonl_schema(mappings_data, required_fields, mappings_file.name, verbose)
    validation_errors += len(schema_errors)
    
    # Collect TPT IDs for validation
    tpt_ids = [mapping.get('tpt_id') for mapping in mappings_data if mapping.get('tpt_id')]
    missing_tpt_ids = get_missing_tpt_ids(con, tpt_ids)
    
    if missing_tpt_ids:
        log_validation_errors(missing_tpt_ids, [], verbose)
        validation_errors += len(missing_tpt_ids)
    
    # Insert valid mappings
    for mapping in mappings_data:
        try:
            tpt_id = mapping.get('tpt_id')
            
            # Skip if TPT ID is missing and we have validation errors
            if not tpt_id and missing_tpt_ids:
                validation_errors += 1
                continue
            
            # Insert into evidence_mapping table
            con.execute("""
                INSERT INTO evidence_mapping (
                    id, food_id, source, tpt_id, taxon_id, part_id, 
                    transforms_json, confidence, disposition, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{source_name}_{mapping['food_id']}",
                mapping['food_id'],
                source_name,
                tpt_id,
                mapping.get('taxon_id', ''),
                mapping.get('part_id', ''),
                json.dumps(mapping.get('transforms', [])),
                mapping.get('confidence', 0.0),
                mapping.get('disposition', 'unknown'),
                mapping.get('reason', ''),
                datetime.now(timezone.utc).isoformat()
            ))
            
            mappings_count += 1
            
        except Exception as e:
            if verbose:
                print(f"    - Warning: Error processing mapping {mapping.get('food_id', 'unknown')}: {e}")
            validation_errors += 1
            continue
    
    return mappings_count, validation_errors

def _load_nutrient_data(con: sqlite3.Connection, nutrients_file: Path, source_name: str, verbose: bool) -> Tuple[int, int]:
    """Load nutrient data from JSONL file with validation"""
    
    # Clear existing nutrient rows for this source
    con.execute("DELETE FROM nutrient_row WHERE source = ?", (source_name,))
    
    nutrient_rows_count = 0
    validation_errors = 0
    
    # Read and validate data
    nutrient_data = list(read_jsonl_safe(nutrients_file, verbose))
    
    # Validate schema
    required_fields = ['food_id', 'nutrient_id', 'amount', 'unit', 'source', 'confidence']
    schema_errors = validate_jsonl_schema(nutrient_data, required_fields, nutrients_file.name, verbose)
    validation_errors += len(schema_errors)
    
    # Collect nutrient IDs for validation
    nutrient_ids = [row.get('nutrient_id') for row in nutrient_data if row.get('nutrient_id')]
    missing_nutrient_ids = get_missing_nutrient_ids(con, nutrient_ids)
    
    if missing_nutrient_ids:
        log_validation_errors([], missing_nutrient_ids, verbose)
        validation_errors += len(missing_nutrient_ids)
    
    # Insert valid nutrient rows
    for nutrient_row in nutrient_data:
        try:
            food_id = nutrient_row.get('food_id')
            nutrient_id = nutrient_row.get('nutrient_id')
            
            # Skip if nutrient ID is missing
            if not nutrient_id or nutrient_id in missing_nutrient_ids:
                validation_errors += 1
                continue
            
            # Get TPT ID from food_id mapping
            tpt_id = None
            if food_id:
                cursor = con.execute(
                    "SELECT tpt_id FROM evidence_mapping WHERE food_id = ? AND source = ?",
                    (food_id, source_name)
                )
                result = cursor.fetchone()
                if result:
                    tpt_id = result[0]
            
            # Insert into nutrient_row table
            con.execute("""
                INSERT INTO nutrient_row (
                    id, food_id, nutrient_id, amount, unit, original_amount, 
                    original_unit, original_nutrient_id, conversion_factor, 
                    source, confidence, notes, created_at, nutrient_name, 
                    nutrient_class, tpt_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{source_name}_{food_id}_{nutrient_id}",
                food_id,
                nutrient_id,
                nutrient_row.get('amount', 0.0),
                nutrient_row.get('unit', ''),
                nutrient_row.get('original_amount', 0.0),
                nutrient_row.get('original_unit', ''),
                nutrient_row.get('original_nutrient_id', ''),
                nutrient_row.get('conversion_factor', 1.0),
                source_name,
                nutrient_row.get('confidence', 0.0),
                nutrient_row.get('notes', ''),
                datetime.now(timezone.utc).isoformat(),
                nutrient_row.get('nutrient_name', ''),
                nutrient_row.get('nutrient_class', ''),
                tpt_id
            ))
            
            nutrient_rows_count += 1
            
        except Exception as e:
            if verbose:
                print(f"    - Warning: Error processing nutrient row {nutrient_row.get('food_id', 'unknown')}: {e}")
            validation_errors += 1
            continue
    
    return nutrient_rows_count, validation_errors
