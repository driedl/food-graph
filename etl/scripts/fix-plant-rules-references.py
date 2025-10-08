#!/usr/bin/env python3
"""
Fix remaining old-format plant taxon ID references in rules files.

This script updates the remaining family-based plant taxon IDs to use the new
clade-based structure in rules files.

Usage: python etl/scripts/fix-plant-rules-references.py [--dry-run] [--backup-dir BACKUP_DIR]
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List
import argparse
from datetime import datetime
import re

# Mapping from old family-based IDs to new clade-based IDs
FAMILY_TO_CLADE_MAPPING = {
    "tx:plantae:anacardiaceae": "tx:plantae:eudicots:sapindales",
    "tx:plantae:juglandaceae": "tx:plantae:eudicots:fagales", 
    "tx:plantae:poaceae": "tx:plantae:monocots:poales",
    "tx:plantae:fabaceae": "tx:plantae:eudicots:fabales",
}

def fix_jsonl_file(file_path: Path, id_mapping: Dict[str, str], dry_run: bool = False) -> int:
    """Fix taxon ID references in a JSONL file"""
    if not file_path.exists():
        return 0
    
    updated_count = 0
    temp_file = file_path.with_suffix('.tmp')
    
    with open(file_path, 'r', encoding='utf-8') as infile, \
         open(temp_file, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            line = line.strip()
            if not line or line.startswith('//'):
                outfile.write(line + '\n')
                continue
            
            try:
                data = json.loads(line)
                original_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
                
                # Update taxon_prefix fields
                if 'taxon_prefix' in data and data['taxon_prefix'] in id_mapping:
                    data['taxon_prefix'] = id_mapping[data['taxon_prefix']]
                    updated_count += 1
                
                # Update applies_to arrays
                if 'applies_to' in data and isinstance(data['applies_to'], list):
                    for item in data['applies_to']:
                        if isinstance(item, dict) and 'taxon_prefix' in item:
                            if item['taxon_prefix'] in id_mapping:
                                item['taxon_prefix'] = id_mapping[item['taxon_prefix']]
                                updated_count += 1
                
                outfile.write(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
                
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON in {file_path}: {e}")
                outfile.write(line + '\n')
    
    if not dry_run and updated_count > 0:
        shutil.move(str(temp_file), str(file_path))
        print(f"Updated {updated_count} references in {file_path.name}")
    else:
        temp_file.unlink()
        if updated_count > 0:
            print(f"Would update {updated_count} references in {file_path.name}")
    
    return updated_count

def verify_mappings(ontology_dir: Path) -> bool:
    """Verify that all mapped IDs exist in the plant data"""
    plantae_dir = ontology_dir / "taxa" / "plantae" / "families"
    plant_ids = set()
    
    # Read all plant taxon IDs
    for file_path in plantae_dir.glob("*.jsonl"):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('//'):
                    try:
                        data = json.loads(line)
                        plant_ids.add(data['id'])
                    except json.JSONDecodeError:
                        continue
    
    # Check if mapped IDs exist
    missing_ids = []
    for new_id in FAMILY_TO_CLADE_MAPPING.values():
        if new_id not in plant_ids:
            missing_ids.append(new_id)
    
    if missing_ids:
        print("ERROR: The following mapped IDs do not exist in plant data:")
        for missing_id in missing_ids:
            print(f"  {missing_id}")
        return False
    
    print("All mapped plant taxon IDs exist")
    return True

def main():
    parser = argparse.ArgumentParser(description="Fix remaining plant taxon ID references in rules")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    parser.add_argument("--backup-dir", default="backups", help="Directory for backups")
    parser.add_argument("--ontology-dir", default="data/ontology", help="Path to ontology directory")
    
    args = parser.parse_args()
    
    ontology_dir = Path(args.ontology_dir)
    backup_dir = Path(args.backup_dir)
    
    if not ontology_dir.exists():
        print(f"ERROR: Ontology directory {ontology_dir} does not exist")
        return 1
    
    if args.dry_run:
        print("DRY RUN - No changes will be made")
    
    # Verify mappings first
    print("Verifying mappings...")
    if not verify_mappings(ontology_dir):
        return 1
    
    # Create backup
    if not args.dry_run:
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"plant_rules_fix_{timestamp}"
        print(f"Creating backup at {backup_path}")
        shutil.copytree(ontology_dir, backup_path)
    
    # Fix rules files
    rules_dir = ontology_dir / "rules"
    total_updated = 0
    
    for file_path in rules_dir.glob("*.jsonl"):
        updated = fix_jsonl_file(file_path, FAMILY_TO_CLADE_MAPPING, args.dry_run)
        total_updated += updated
    
    print(f"\nFix complete!")
    print(f"Total references updated: {total_updated}")
    
    if not args.dry_run:
        print(f"Backup created at: {backup_path}")
    
    return 0

if __name__ == "__main__":
    exit(main())
