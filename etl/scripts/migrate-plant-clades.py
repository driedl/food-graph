#!/usr/bin/env python3
"""
Migration script to update plant taxon IDs from family-based to clade-based structure.

This script:
1. Maps plant families to their clades (eudicots/monocots/gymnosperms)
2. Updates all taxon IDs in the ontology
3. Updates all references to these IDs across the entire ontology
4. Preserves all relationships and data integrity

Usage: python scripts/migrate-plant-clades.py [--dry-run] [--backup-dir BACKUP_DIR]
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple
import argparse
from datetime import datetime

# Mapping from family names to clades
FAMILY_TO_CLADE = {
    # Monocots
    "poaceae": "monocots",  # Grasses (rice, wheat, corn, etc.)
    "musaceae": "monocots",  # Bananas
    "zingiberaceae": "monocots",  # Ginger, turmeric
    "asparagaceae": "monocots",  # Asparagus
    "amaryllidaceae": "monocots",  # Onions, garlic
    "bromeliaceae": "monocots",  # Pineapple
    "arecaceae": "monocots",  # Palms (coconut)
    
    # Gymnosperms
    "pinaceae": "gymnosperms",  # Pines (pine nuts)
    
    # Eudicots (everything else)
    "anacardiaceae": "eudicots",  # Mango, cashew, pistachio
    "brassicaceae": "eudicots",  # Cabbage, mustard, broccoli
    "fabaceae": "eudicots",  # Beans, peas, lentils, peanuts
    "rosaceae": "eudicots",  # Apples, pears, strawberries, almonds
    "solanaceae": "eudicots",  # Tomatoes, potatoes, peppers
    "cucurbitaceae": "eudicots",  # Squash, pumpkin, cucumber
    "asteraceae": "eudicots",  # Lettuce, sunflower
    "lamiaceae": "eudicots",  # Mint, basil, oregano
    "apiaceae": "eudicots",  # Carrot, celery, parsley
    "rutaceae": "eudicots",  # Citrus
    "oleaceae": "eudicots",  # Olive
    "lauraceae": "eudicots",  # Avocado, cinnamon, bay
    "vitaceae": "eudicots",  # Grapes
    "juglandaceae": "eudicots",  # Walnuts, pecans
    "fagaceae": "eudicots",  # Chestnuts, beeches
    "betulaceae": "eudicots",  # Hazelnuts
    "ericaceae": "eudicots",  # Blueberries, cranberries
    "myrtaceae": "eudicots",  # Cloves, allspice
    "myristicaceae": "eudicots",  # Nutmeg
    "lecythidaceae": "eudicots",  # Brazil nuts
    "proteaceae": "eudicots",  # Macadamia
    "piperaceae": "eudicots",  # Black pepper
    "pedaliaceae": "eudicots",  # Sesame
    "linaceae": "eudicots",  # Flax
    "polygonaceae": "eudicots",  # Buckwheat, rhubarb
    "amaranthaceae": "eudicots",  # Amaranth, quinoa
    "euphorbiaceae": "eudicots",  # Cassava
    "convolvulaceae": "eudicots",  # Sweet potato
    "actinidiaceae": "eudicots",  # Kiwifruit
    "annonaceae": "eudicots",  # Custard apples
}

# Orders for each clade (needed for the new structure)
CLADE_ORDERS = {
    "monocots": {
        "poaceae": "poales",
        "musaceae": "zingiberales", 
        "zingiberaceae": "zingiberales",
        "asparagaceae": "asparagales",
        "amaryllidaceae": "asparagales",
        "bromeliaceae": "poales",
        "arecaceae": "arecales",
    },
    "gymnosperms": {
        "pinaceae": "pinales",
    },
    "eudicots": {
        "anacardiaceae": "sapindales",
        "brassicaceae": "brassicales",
        "fabaceae": "fabales",
        "rosaceae": "rosales",
        "solanaceae": "solanales",
        "cucurbitaceae": "cucurbitales",
        "asteraceae": "asterales",
        "lamiaceae": "lamiales",
        "apiaceae": "apiales",
        "rutaceae": "sapindales",
        "oleaceae": "lamiales",
        "lauraceae": "laurales",
        "vitaceae": "vitales",
        "juglandaceae": "fagales",
        "fagaceae": "fagales",
        "betulaceae": "fagales",
        "ericaceae": "ericales",
        "myrtaceae": "myrtales",
        "myristicaceae": "magnoliales",
        "lecythidaceae": "ericales",
        "proteaceae": "proteales",
        "piperaceae": "piperales",
        "pedaliaceae": "lamiales",
        "linaceae": "malpighiales",
        "polygonaceae": "caryophyllales",
        "amaranthaceae": "caryophyllales",
        "euphorbiaceae": "malpighiales",
        "convolvulaceae": "solanales",
        "actinidiaceae": "ericales",
        "annonaceae": "magnoliales",
    }
}

def get_family_from_taxon_id(taxon_id: str) -> str:
    """Extract family name from taxon ID like 'tx:plantae:brassicaceae'"""
    if not taxon_id.startswith("tx:plantae:"):
        return None
    parts = taxon_id.split(":")
    if len(parts) >= 3:
        return parts[2]  # The family name
    return None

def create_new_taxon_id(old_id: str, family: str, clade: str) -> str:
    """Create new taxon ID with clade structure"""
    if not old_id.startswith("tx:plantae:"):
        return old_id
    
    parts = old_id.split(":")
    if len(parts) < 3:
        return old_id
    
    # Get the order for this family
    order = CLADE_ORDERS.get(clade, {}).get(family)
    if not order:
        print(f"WARNING: No order found for family {family} in clade {clade}")
        return old_id
    
    # Reconstruct with clade and order
    new_parts = ["tx", "plantae", clade, order] + parts[3:]
    return ":".join(new_parts)

def update_taxon_id_mapping(old_id: str, family: str, clade: str) -> str:
    """Update a single taxon ID"""
    return create_new_taxon_id(old_id, family, clade)

def process_jsonl_file(file_path: Path, id_mapping: Dict[str, str], dry_run: bool = False) -> int:
    """Process a JSONL file and update taxon IDs"""
    if not file_path.exists():
        return 0
    
    updated_count = 0
    temp_file = file_path.with_suffix('.tmp')
    
    with open(file_path, 'r', encoding='utf-8') as infile, \
         open(temp_file, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            line = line.strip()
            if not line or line.startswith('//'):
                outfile.write(line + '\n')
                continue
            
            try:
                data = json.loads(line)
                updated = False
                
                # Update taxon_id if present
                if 'taxon_id' in data and data['taxon_id'] in id_mapping:
                    data['taxon_id'] = id_mapping[data['taxon_id']]
                    updated = True
                
                # Update parent if present
                if 'parent' in data and data['parent'] in id_mapping:
                    data['parent'] = id_mapping[data['parent']]
                    updated = True
                
                # Update any other fields that might contain taxon IDs
                for key, value in data.items():
                    if isinstance(value, str) and value.startswith('tx:plantae:'):
                        if value in id_mapping:
                            data[key] = id_mapping[value]
                            updated = True
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            if isinstance(item, str) and item.startswith('tx:plantae:'):
                                if item in id_mapping:
                                    data[key][i] = id_mapping[item]
                                    updated = True
                
                if updated:
                    updated_count += 1
                
                outfile.write(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
                
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON in {file_path} at line {line_num}: {e}")
                outfile.write(line + '\n')
    
    if not dry_run and updated_count > 0:
        shutil.move(str(temp_file), str(file_path))
    else:
        temp_file.unlink()
    
    return updated_count

def process_json_file(file_path: Path, id_mapping: Dict[str, str], dry_run: bool = False) -> int:
    """Process a JSON file and update taxon IDs"""
    if not file_path.exists():
        return 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        updated_count = 0
        
        def update_recursive(obj):
            nonlocal updated_count
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and value.startswith('tx:plantae:'):
                        if value in id_mapping:
                            obj[key] = id_mapping[value]
                            updated_count += 1
                    elif isinstance(value, (dict, list)):
                        update_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        update_recursive(item)
        
        update_recursive(data)
        
        if not dry_run and updated_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return updated_count
        
    except Exception as e:
        print(f"ERROR: Failed to process {file_path}: {e}")
        return 0

def process_markdown_file(file_path: Path, id_mapping: Dict[str, str], dry_run: bool = False) -> int:
    """Process a Markdown file and update taxon IDs in YAML frontmatter"""
    if not file_path.exists():
        return 0
    
    updated_count = 0
    temp_file = file_path.with_suffix('.tmp')
    
    with open(file_path, 'r', encoding='utf-8') as infile, \
         open(temp_file, 'w', encoding='utf-8') as outfile:
        
        content = infile.read()
        original_content = content
        
        # Update taxon IDs in the content
        for old_id, new_id in id_mapping.items():
            if old_id in content:
                content = content.replace(old_id, new_id)
                updated_count += 1
        
        outfile.write(content)
    
    if not dry_run and updated_count > 0:
        shutil.move(str(temp_file), str(file_path))
    else:
        temp_file.unlink()
    
    return updated_count

def build_id_mapping(ontology_dir: Path) -> Dict[str, str]:
    """Build mapping from old taxon IDs to new taxon IDs"""
    id_mapping = {}
    
    # Process all plant family files
    plantae_dir = ontology_dir / "taxa" / "plantae" / "families"
    
    for file_path in plantae_dir.glob("*.jsonl"):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('//'):
                    continue
                
                try:
                    data = json.loads(line)
                    old_id = data.get('id')
                    if old_id and old_id.startswith('tx:plantae:'):
                        family = get_family_from_taxon_id(old_id)
                        if family and family in FAMILY_TO_CLADE:
                            clade = FAMILY_TO_CLADE[family]
                            new_id = update_taxon_id_mapping(old_id, family, clade)
                            id_mapping[old_id] = new_id
                            
                except json.JSONDecodeError:
                    continue
    
    return id_mapping

def create_backup(ontology_dir: Path, backup_dir: Path):
    """Create backup of ontology directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"ontology_backup_{timestamp}"
    
    print(f"Creating backup at {backup_path}")
    shutil.copytree(ontology_dir, backup_path)
    return backup_path

def main():
    parser = argparse.ArgumentParser(description="Migrate plant taxon IDs to clade-based structure")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    parser.add_argument("--backup-dir", default="backups", help="Directory for backups")
    parser.add_argument("--ontology-dir", default="data/ontology", help="Path to ontology directory")
    
    args = parser.parse_args()
    
    ontology_dir = Path(args.ontology_dir)
    backup_dir = Path(args.backup_dir)
    
    if not ontology_dir.exists():
        print(f"ERROR: Ontology directory {ontology_dir} does not exist")
        return 1
    
    print("Building taxon ID mapping...")
    id_mapping = build_id_mapping(ontology_dir)
    
    if not id_mapping:
        print("No plant taxon IDs found to migrate")
        return 0
    
    print(f"Found {len(id_mapping)} taxon IDs to migrate")
    
    if args.dry_run:
        print("\nDRY RUN - No changes will be made")
        print("Sample mappings:")
        for i, (old_id, new_id) in enumerate(list(id_mapping.items())[:10]):
            print(f"  {old_id} -> {new_id}")
        if len(id_mapping) > 10:
            print(f"  ... and {len(id_mapping) - 10} more")
        return 0
    
    # Create backup
    backup_dir.mkdir(exist_ok=True)
    backup_path = create_backup(ontology_dir, backup_dir)
    
    total_updated = 0
    
    # Process all files in ontology directory
    for file_path in ontology_dir.rglob("*"):
        if file_path.is_file():
            if file_path.suffix == '.jsonl':
                updated = process_jsonl_file(file_path, id_mapping, args.dry_run)
            elif file_path.suffix == '.json':
                updated = process_json_file(file_path, id_mapping, args.dry_run)
            elif file_path.suffix == '.md':
                updated = process_markdown_file(file_path, id_mapping, args.dry_run)
            else:
                continue
            
            if updated > 0:
                print(f"Updated {updated} references in {file_path.relative_to(ontology_dir)}")
                total_updated += updated
    
    print(f"\nMigration complete!")
    print(f"Total references updated: {total_updated}")
    print(f"Backup created at: {backup_path}")
    
    return 0

if __name__ == "__main__":
    exit(main())
