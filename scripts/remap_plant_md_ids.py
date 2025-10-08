#!/usr/bin/env python3
"""
Remap plant .md file IDs to include family level to match plants_fixed_ids.jsonl structure.
"""
import json
import re
from pathlib import Path

def load_plant_mapping(plants_file: Path) -> dict:
    """Load the mapping from old IDs to new IDs from plants_fixed_ids.jsonl"""
    mapping = {}
    
    with open(plants_file, 'r') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                id_parts = data['id'].split(':')
                
                # For family level, create mapping from old format to new format
                if data['rank'] == 'family' and len(id_parts) >= 4:
                    # Extract: kingdom:clade:order:family
                    kingdom, clade, order, family = id_parts[1:5]
                    old_id = f"tx:{kingdom}:{clade}:{order}"
                    new_id = f"tx:{kingdom}:{clade}:{order}:{family}"
                    mapping[old_id] = new_id
                
                # For genus level, create mapping from old format to new format
                elif data['rank'] == 'genus' and len(id_parts) >= 5:
                    # Extract: kingdom:clade:order:family:genus
                    kingdom, clade, order, family, genus = id_parts[1:6]
                    old_id = f"tx:{kingdom}:{clade}:{order}:{genus}"
                    new_id = f"tx:{kingdom}:{clade}:{order}:{family}:{genus}"
                    mapping[old_id] = new_id
                    
                # For species level, create mapping from old format to new format  
                elif data['rank'] == 'species' and len(id_parts) >= 6:
                    kingdom, clade, order, family, genus, species = id_parts[1:7]
                    old_id = f"tx:{kingdom}:{clade}:{order}:{genus}:{species}"
                    new_id = f"tx:{kingdom}:{clade}:{order}:{family}:{genus}:{species}"
                    mapping[old_id] = new_id
    
    return mapping

def update_md_file(file_path: Path, mapping: dict) -> bool:
    """Update a single .md file with new IDs"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the id field in frontmatter
        id_match = re.search(r'^id:\s*(.+)$', content, re.MULTILINE)
        if not id_match:
            print(f"Warning: No id field found in {file_path}")
            return False
            
        old_id = id_match.group(1).strip()
        if old_id in mapping:
            new_id = mapping[old_id]
            new_content = content.replace(f'id: {old_id}', f'id: {new_id}')
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"Updated {file_path}: {old_id} -> {new_id}")
            return True
        else:
            print(f"Warning: No mapping found for {old_id} in {file_path}")
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    plants_file = Path("data/ontology/taxa/plantae/plants_fixed_ids.jsonl")
    families_dir = Path("data/ontology/taxa/plantae/families")
    
    if not plants_file.exists():
        print(f"Error: {plants_file} not found")
        return 1
        
    if not families_dir.exists():
        print(f"Error: {families_dir} not found")
        return 1
    
    print("Loading plant ID mapping...")
    mapping = load_plant_mapping(plants_file)
    print(f"Loaded {len(mapping)} ID mappings")
    
    # Process all .md files in families directory
    md_files = list(families_dir.glob("*.tx.md"))
    print(f"Found {len(md_files)} .md files to process")
    
    updated_count = 0
    for md_file in md_files:
        if update_md_file(md_file, mapping):
            updated_count += 1
    
    print(f"Successfully updated {updated_count}/{len(md_files)} files")
    return 0

if __name__ == "__main__":
    exit(main())
