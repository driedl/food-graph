#!/usr/bin/env python3
"""
Fix plant clade structure by creating missing clade nodes and updating parent relationships.

This script:
1. Creates the missing clade nodes (tx:plantae:eudicots, tx:plantae:monocots, tx:plantae:gymnosperms)
2. Updates family parent relationships to point to clade nodes instead of tx:plantae
3. Ensures proper lineage up to "life"

Usage: python etl/scripts/fix-plant-clade-nodes.py [--dry-run] [--backup-dir BACKUP_DIR]
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple
import argparse
from datetime import datetime

# Clade definitions
CLADES = {
    "eudicots": {
        "display_name": "Eudicots",
        "latin_name": "Eudicotyledoneae",
        "description": "The largest clade of flowering plants, characterized by tricolpate pollen"
    },
    "monocots": {
        "display_name": "Monocots", 
        "latin_name": "Monocotyledoneae",
        "description": "Flowering plants with a single cotyledon, including grasses, lilies, and orchids"
    },
    "gymnosperms": {
        "display_name": "Gymnosperms",
        "latin_name": "Gymnospermae", 
        "description": "Seed plants that do not produce flowers, including conifers and cycads"
    }
}

# Mapping from clade to orders (for family parent relationships)
CLADE_ORDERS = {
    "eudicots": [
        "sapindales", "brassicales", "fabales", "rosales", "solanales", "cucurbitales",
        "asterales", "lamiales", "apiales", "laurales", "vitales", "fagales", "ericales",
        "myrtales", "magnoliales", "proteales", "piperales", "malpighiales", "caryophyllales"
    ],
    "monocots": [
        "poales", "zingiberales", "asparagales", "arecales"
    ],
    "gymnosperms": [
        "pinales"
    ]
}

def create_clade_nodes(ontology_dir: Path, dry_run: bool = False) -> int:
    """Create the missing clade nodes"""
    plantae_index = ontology_dir / "taxa" / "index.jsonl"
    
    if not plantae_index.exists():
        print(f"ERROR: {plantae_index} does not exist")
        return 0
    
    # Read existing index
    with open(plantae_index, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find where to insert clade nodes (after tx:plantae)
    insert_index = 0
    for i, line in enumerate(lines):
        if '"id": "tx:plantae"' in line:
            insert_index = i + 1
            break
    
    # Create clade node entries
    clade_entries = []
    for clade_id, clade_info in CLADES.items():
        clade_entry = {
            "id": f"tx:plantae:{clade_id}",
            "parent": "tx:plantae",
            "rank": "clade",
            "display_name": clade_info["display_name"],
            "latin_name": clade_info["latin_name"],
            "aliases": [],
            "description": clade_info["description"]
        }
        clade_entries.append(json.dumps(clade_entry, ensure_ascii=False, separators=(',', ':')))
    
    # Insert clade nodes
    new_lines = lines[:insert_index] + [entry + '\n' for entry in clade_entries] + lines[insert_index:]
    
    if not dry_run:
        with open(plantae_index, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    
    print(f"Created {len(clade_entries)} clade nodes")
    return len(clade_entries)

def update_family_parents(ontology_dir: Path, dry_run: bool = False) -> int:
    """Update family parent relationships to point to clade nodes"""
    plantae_dir = ontology_dir / "taxa" / "plantae" / "families"
    updated_count = 0
    
    for file_path in plantae_dir.glob("*.jsonl"):
        temp_file = file_path.with_suffix('.tmp')
        file_updated = False
        
        with open(file_path, 'r', encoding='utf-8') as infile, \
             open(temp_file, 'w', encoding='utf-8') as outfile:
            
            for line in infile:
                line = line.strip()
                if not line or line.startswith('//'):
                    outfile.write(line + '\n')
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # Check if this is a family node that needs parent update
                    if (data.get('rank') == 'family' and 
                        data.get('parent') == 'tx:plantae' and
                        ':' in data.get('id', '')):
                        
                        # Extract clade from ID (e.g., tx:plantae:eudicots:sapindales -> eudicots)
                        id_parts = data['id'].split(':')
                        if len(id_parts) >= 3:
                            clade = id_parts[2]  # eudicots, monocots, or gymnosperms
                            if clade in CLADES:
                                data['parent'] = f"tx:plantae:{clade}"
                                file_updated = True
                                updated_count += 1
                    
                    outfile.write(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
                    
                except json.JSONDecodeError as e:
                    print(f"ERROR: Invalid JSON in {file_path}: {e}")
                    outfile.write(line + '\n')
        
        if not dry_run and file_updated:
            shutil.move(str(temp_file), str(file_path))
        else:
            temp_file.unlink()
    
    return updated_count

def verify_lineage(ontology_dir: Path) -> bool:
    """Verify that all plant taxa have proper lineage up to 'life'"""
    plantae_dir = ontology_dir / "taxa" / "plantae" / "families"
    
    # Build parent map
    parent_map = {}
    
    # Read index file
    index_file = ontology_dir / "taxa" / "index.jsonl"
    with open(index_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            try:
                data = json.loads(line)
                parent_map[data['id']] = data.get('parent')
            except json.JSONDecodeError:
                continue
    
    # Read all family files
    for file_path in plantae_dir.glob("*.jsonl"):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('//'):
                    continue
                try:
                    data = json.loads(line)
                    parent_map[data['id']] = data.get('parent')
                except json.JSONDecodeError:
                    continue
    
    # Verify lineage for each taxon
    errors = []
    for taxon_id, parent_id in parent_map.items():
        if not parent_id:
            continue
            
        # Trace lineage up to root
        current_id = taxon_id
        lineage = [current_id]
        
        while current_id in parent_map and parent_map[current_id]:
            current_id = parent_map[current_id]
            lineage.append(current_id)
            
            # Prevent infinite loops
            if len(lineage) > 10:
                errors.append(f"Infinite loop detected for {taxon_id}")
                break
        
        # Check if we reach tx:life
        if lineage[-1] != "tx:life":
            errors.append(f"Taxon {taxon_id} does not trace to tx:life. Lineage: {' -> '.join(lineage)}")
    
    if errors:
        print("Lineage verification errors:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
        return False
    
    print("All lineages verified successfully")
    return True

def main():
    parser = argparse.ArgumentParser(description="Fix plant clade structure")
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
    
    # Create backup
    if not args.dry_run:
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"ontology_clade_fix_{timestamp}"
        print(f"Creating backup at {backup_path}")
        shutil.copytree(ontology_dir, backup_path)
    
    # Step 1: Create clade nodes
    print("Creating clade nodes...")
    clade_count = create_clade_nodes(ontology_dir, args.dry_run)
    
    # Step 2: Update family parent relationships
    print("Updating family parent relationships...")
    family_count = update_family_parents(ontology_dir, args.dry_run)
    
    # Step 3: Verify lineage
    print("Verifying lineage...")
    if not args.dry_run:
        lineage_ok = verify_lineage(ontology_dir)
        if not lineage_ok:
            print("WARNING: Lineage verification failed")
            return 1
    
    print(f"\nFix complete!")
    print(f"Created {clade_count} clade nodes")
    print(f"Updated {family_count} family parent relationships")
    
    if not args.dry_run:
        print(f"Backup created at: {backup_path}")
    
    return 0

if __name__ == "__main__":
    exit(main())
