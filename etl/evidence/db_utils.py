#!/usr/bin/env python3
"""
Database Utilities for Evidence Processing

Shared utilities for database operations, error handling, and validation.
"""

from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timezone

@contextmanager
def get_db_connection(db_path: Path, verbose: bool = False):
    """Context manager for database connections with proper error handling."""
    con = None
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("PRAGMA foreign_keys=ON")
        if verbose:
            print(f"  • Connected to database: {db_path}")
        yield con
    except Exception as e:
        if con:
            con.rollback()
        raise Exception(f"Database operation failed: {e}")
    finally:
        if con:
            con.close()

def validate_tpt_exists(con: sqlite3.Connection, tpt_id: str) -> bool:
    """Validate that TPT ID exists in tpt_nodes table."""
    if not tpt_id:
        return False
    
    cursor = con.execute("SELECT 1 FROM tpt_nodes WHERE id = ?", (tpt_id,))
    return cursor.fetchone() is not None

def validate_nutrient_exists(con: sqlite3.Connection, nutrient_id: str) -> bool:
    """Validate that nutrient ID exists in nutrients table."""
    if not nutrient_id:
        return False
    
    cursor = con.execute("SELECT 1 FROM nutrients WHERE id = ?", (nutrient_id,))
    return cursor.fetchone() is not None

def get_missing_tpt_ids(con: sqlite3.Connection, tpt_ids: List[str]) -> List[str]:
    """Get list of TPT IDs that don't exist in the database."""
    if not tpt_ids:
        return []
    
    placeholders = ','.join('?' for _ in tpt_ids)
    cursor = con.execute(f"SELECT id FROM tpt_nodes WHERE id IN ({placeholders})", tpt_ids)
    existing_ids = {row[0] for row in cursor.fetchall()}
    return [tpt_id for tpt_id in tpt_ids if tpt_id not in existing_ids]

def get_missing_nutrient_ids(con: sqlite3.Connection, nutrient_ids: List[str]) -> List[str]:
    """Get list of nutrient IDs that don't exist in the database."""
    if not nutrient_ids:
        return []
    
    placeholders = ','.join('?' for _ in nutrient_ids)
    cursor = con.execute(f"SELECT id FROM nutrients WHERE id IN ({placeholders})", nutrient_ids)
    existing_ids = {row[0] for row in cursor.fetchall()}
    return [nutrient_id for nutrient_id in nutrient_ids if nutrient_id not in existing_ids]

def log_validation_errors(missing_tpt_ids: List[str], missing_nutrient_ids: List[str], 
                         verbose: bool = False) -> None:
    """Log validation errors in a consistent format."""
    if missing_tpt_ids:
        error_msg = f"Missing TPT IDs in database: {missing_tpt_ids[:5]}{'...' if len(missing_tpt_ids) > 5 else ''}"
        if verbose:
            print(f"  ⚠️  {error_msg}")
        else:
            print(f"ERROR: {error_msg}")
    
    if missing_nutrient_ids:
        error_msg = f"Missing nutrient IDs in database: {missing_nutrient_ids[:5]}{'...' if len(missing_nutrient_ids) > 5 else ''}"
        if verbose:
            print(f"  ⚠️  {error_msg}")
        else:
            print(f"ERROR: {error_msg}")

def create_evidence_stats() -> Dict[str, int]:
    """Create standardized evidence processing statistics."""
    return {
        'sources_loaded': 0,
        'mappings_loaded': 0,
        'nutrient_rows_loaded': 0,
        'validation_errors': 0,
        'skipped_rows': 0
    }

def create_rollup_stats() -> Dict[str, int]:
    """Create standardized rollup processing statistics."""
    return {
        'tpts_processed': 0,
        'profiles_computed': 0,
        'validation_errors': 0,
        'skipped_groups': 0
    }

def log_stats(stats: Dict[str, int], stage_name: str, verbose: bool = False) -> None:
    """Log statistics in a consistent format."""
    if verbose:
        print(f"  • {stage_name} Statistics:")
        for key, value in stats.items():
            if value > 0:
                print(f"    - {key}: {value}")
    else:
        # Summary format for non-verbose
        total_processed = sum(v for k, v in stats.items() if 'processed' in k or 'loaded' in k or 'computed' in k)
        errors = stats.get('validation_errors', 0) + stats.get('skipped_rows', 0) + stats.get('skipped_groups', 0)
        print(f"  • {stage_name}: {total_processed} processed, {errors} errors/skipped")
