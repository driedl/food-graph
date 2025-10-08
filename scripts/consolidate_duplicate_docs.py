#!/usr/bin/env python3
"""
Consolidate duplicate documentation files for the same taxon ID.
Keep the most comprehensive one and remove duplicates.
"""
import re
from pathlib import Path
from collections import defaultdict

def get_taxon_id(file_path: Path) -> str:
    """Extract taxon ID from a .md file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        id_match = re.search(r'^id:\s*(.+)$', content, re.MULTILINE)
        if id_match:
            return id_match.group(1).strip()
        return ""
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

def get_file_priority(file_path: Path) -> int:
    """Determine priority for keeping files (lower number = higher priority)"""
    filename = file_path.stem.lower()
    
    # Priority order: family files first, then specific ones
    if '--' in filename:
        name_part = filename.split('--')[0]
        if name_part.endswith('aceae') or name_part.endswith('idae'):
            return 1  # Family files have highest priority
        elif 'family' in filename:
            return 2  # Files with "family" in name
        else:
            return 3  # Specific genus/species files
    else:
        return 4  # Generic files

def consolidate_duplicates(families_dir: Path) -> int:
    """Consolidate duplicate documentation files"""
    # Group files by taxon ID
    files_by_id = defaultdict(list)
    
    for md_file in families_dir.glob("*.tx.md"):
        taxon_id = get_taxon_id(md_file)
        if taxon_id:
            files_by_id[taxon_id].append(md_file)
    
    # Find duplicates
    duplicates = {tid: files for tid, files in files_by_id.items() if len(files) > 1}
    
    if not duplicates:
        print("No duplicate taxon IDs found")
        return 0
    
    print(f"Found {len(duplicates)} taxon IDs with duplicates:")
    for taxon_id, files in duplicates.items():
        print(f"  {taxon_id}: {len(files)} files")
    
    # Consolidate duplicates
    removed_count = 0
    for taxon_id, files in duplicates.items():
        # Sort by priority (keep the best one)
        files.sort(key=get_file_priority)
        keep_file = files[0]
        remove_files = files[1:]
        
        print(f"\nKeeping: {keep_file.name}")
        for remove_file in remove_files:
            print(f"Removing: {remove_file.name}")
            remove_file.unlink()
            removed_count += 1
    
    print(f"\nRemoved {removed_count} duplicate files")
    return removed_count

def main():
    families_dir = Path("data/ontology/taxa/plantae/families")
    
    if not families_dir.exists():
        print(f"Error: {families_dir} not found")
        return 1
    
    print("Consolidating duplicate documentation files...")
    removed_count = consolidate_duplicates(families_dir)
    
    if removed_count > 0:
        print(f"Successfully consolidated duplicates. Removed {removed_count} files.")
    else:
        print("No duplicates found to consolidate.")
    
    return 0

if __name__ == "__main__":
    exit(main())
