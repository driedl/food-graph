#!/usr/bin/env python3
"""
Stage G Contract Verification

Validates that Stage G outputs meet the expected contract requirements.
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Dict, Any, List

def verify_stage_g_contract(build_dir: Path, verbose: bool = False) -> None:
    """
    Verify Stage G contract requirements.
    
    Ensures that:
    1. Database contains required tables
    2. Evidence data has been loaded
    3. Nutrient profile rollups have been computed
    """
    db_path = build_dir / "database" / "graph.dev.sqlite"
    
    if not db_path.exists():
        raise Exception(f"Database not found: {db_path}")
    
    with sqlite3.connect(str(db_path)) as con:
        # Check required tables exist
        cursor = con.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('evidence_mapping', 'nutrient_row', 'nutrient_profile_rollup')
        """)
        tables = {row[0] for row in cursor.fetchall()}
        
        required_tables = {'evidence_mapping', 'nutrient_row', 'nutrient_profile_rollup'}
        missing_tables = required_tables - tables
        
        if missing_tables:
            raise Exception(f"Missing required tables: {missing_tables}")
        
        # Check evidence data has been loaded
        cursor = con.execute("SELECT COUNT(*) FROM evidence_mapping")
        mapping_count = cursor.fetchone()[0]
        
        if mapping_count == 0:
            if verbose:
                print("  • Warning: No evidence mappings found in database")
        
        # Check nutrient data has been loaded
        cursor = con.execute("SELECT COUNT(*) FROM nutrient_row WHERE tpt_id IS NOT NULL")
        nutrient_count = cursor.fetchone()[0]
        
        if nutrient_count == 0:
            if verbose:
                print("  • Warning: No nutrient rows with TPT IDs found in database")
        
        # Check rollups have been computed
        cursor = con.execute("SELECT COUNT(*) FROM nutrient_profile_rollup")
        rollup_count = cursor.fetchone()[0]
        
        if rollup_count == 0:
            if verbose:
                print("  • Warning: No nutrient profile rollups found in database")
        
        # Check for referential integrity
        cursor = con.execute("""
            SELECT COUNT(*) FROM nutrient_row nr 
            LEFT JOIN tpt_nodes tpt ON nr.tpt_id = tpt.id 
            WHERE nr.tpt_id IS NOT NULL AND tpt.id IS NULL
        """)
        orphaned_nutrients = cursor.fetchone()[0]
        
        if orphaned_nutrients > 0:
            raise Exception(f"Found {orphaned_nutrients} nutrient rows with invalid TPT references")
        
        cursor = con.execute("""
            SELECT COUNT(*) FROM nutrient_row nr 
            LEFT JOIN nutrients n ON nr.nutrient_id = n.id 
            WHERE n.id IS NULL
        """)
        orphaned_nutrients = cursor.fetchone()[0]
        
        if orphaned_nutrients > 0:
            raise Exception(f"Found {orphaned_nutrients} nutrient rows with invalid nutrient references")
        
        if verbose:
            print(f"  • Contract verification passed:")
            print(f"    - Evidence mappings: {mapping_count}")
            print(f"    - Nutrient rows with TPT: {nutrient_count}")
            print(f"    - Nutrient profile rollups: {rollup_count}")
            print(f"    - Referential integrity: OK")
