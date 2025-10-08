#!/usr/bin/env python3
"""
Fix orphaned fungi taxon ID references in Markdown files.

This script updates the old genus-level taxon IDs in Markdown files to point to the correct
full hierarchical IDs in the new fungi structure.

Usage: python etl/scripts/fix-fungi-references.py [--dry-run] [--backup-dir BACKUP_DIR]
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List
import argparse
from datetime import datetime

# Mapping from old genus-level IDs to new full hierarchical IDs
FUNGI_ID_MAPPING = {
    "tx:fungi:hypsizygus": "tx:fungi:agaricomycetes:agaricales:lyophyllaceae:hypsizygus",
    "tx:fungi:grifola": "tx:fungi:agaricomycetes:polyporales:meripilaceae:grifola", 
    "tx:fungi:flammulina": "tx:fungi:agaricomycetes:agaricales:physalacriaceae:flammulina",
    "tx:fungi:lentinula": "tx:fungi:agaricomycetes:agaricales:omphalotaceae:lentinula",
    "tx:fungi:agrocybe": "tx:fungi:agaricomycetes:agaricales:strophariaceae:cyclocybe",  # Note: Agrocybe was renamed to Cyclocybe
    "tx:fungi:agaricus": "tx:fungi:agaricomycetes:agaricales:agaricaceae:agaricus",
    "tx:fungi:hericium": "tx:fungi:agaricomycetes:russulales:hericiaceae:hericium",
    "tx:fungi:pleurotus": "tx:fungi:agaricomycetes:agaricales:pleurotaceae:pleurotus",
}

def fix_markdown_file(file_path: Path, id_mapping: Dict[str, str], dry_run: bool = False) -> int:
    """Fix taxon ID references in a Markdown file"""
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
        print(f"Updated {updated_count} references in {file_path.name}")
    else:
        temp_file.unlink()
        if updated_count > 0:
            print(f"Would update {updated_count} references in {file_path.name}")
    
    return updated_count

def verify_fungi_structure(ontology_dir: Path) -> bool:
    """Verify that all fungi taxon IDs exist in the fungi.jsonl file"""
    fungi_file = ontology_dir / "taxa" / "fungi" / "fungi.jsonl"
    
    if not fungi_file.exists():
        print(f"ERROR: {fungi_file} does not exist")
        return False
    
    # Read all fungi taxon IDs
    fungi_ids = set()
    with open(fungi_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            try:
                data = json.loads(line)
                fungi_ids.add(data['id'])
            except json.JSONDecodeError:
                continue
    
    # Check if all mapped IDs exist
    missing_ids = []
    for new_id in FUNGI_ID_MAPPING.values():
        if new_id not in fungi_ids:
            missing_ids.append(new_id)
    
    if missing_ids:
        print("ERROR: The following mapped IDs do not exist in fungi.jsonl:")
        for missing_id in missing_ids:
            print(f"  {missing_id}")
        return False
    
    print("All mapped fungi taxon IDs exist in fungi.jsonl")
    return True

def main():
    parser = argparse.ArgumentParser(description="Fix orphaned fungi taxon ID references")
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
    
    # Verify fungi structure first
    print("Verifying fungi structure...")
    if not verify_fungi_structure(ontology_dir):
        return 1
    
    # Create backup
    if not args.dry_run:
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"fungi_references_fix_{timestamp}"
        print(f"Creating backup at {backup_path}")
        shutil.copytree(ontology_dir, backup_path)
    
    # Find and fix Markdown files
    fungi_dir = ontology_dir / "taxa" / "fungi"
    total_updated = 0
    
    for file_path in fungi_dir.glob("*.md"):
        updated = fix_markdown_file(file_path, FUNGI_ID_MAPPING, args.dry_run)
        total_updated += updated
    
    print(f"\nFix complete!")
    print(f"Total references updated: {total_updated}")
    
    if not args.dry_run:
        print(f"Backup created at: {backup_path}")
    
    return 0

if __name__ == "__main__":
    exit(main())
