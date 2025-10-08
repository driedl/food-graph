#!/usr/bin/env python3
"""
Fix plant .md file IDs by matching the latin_name in the file to the correct ID in plants_fixed_ids.jsonl.
"""
import json
import re
from pathlib import Path

def load_genus_mapping(plants_file: Path) -> dict:
    """Load genus mappings from plants_fixed_ids.jsonl by latin_name"""
    genera = {}
    
    with open(plants_file, 'r') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                if data['rank'] == 'genus':
                    latin_name = data['latin_name'].lower()
                    genera[latin_name] = data['id']
    
    return genera

def update_md_file(file_path: Path, genus_mapping: dict) -> bool:
    """Update a single .md file with the correct genus ID"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the latin_name field in frontmatter
        latin_match = re.search(r'^latin_name:\s*(.+)$', content, re.MULTILINE)
        if not latin_match:
            print(f"Warning: No latin_name field found in {file_path}")
            return False
            
        latin_name = latin_match.group(1).strip().lower()
        
        # Find the id field
        id_match = re.search(r'^id:\s*(.+)$', content, re.MULTILINE)
        if not id_match:
            print(f"Warning: No id field found in {file_path}")
            return False
            
        current_id = id_match.group(1).strip()
        
        # Get the correct genus ID
        if latin_name in genus_mapping:
            correct_id = genus_mapping[latin_name]
            
            if current_id != correct_id:
                # Update the ID
                new_content = content.replace(f'id: {current_id}', f'id: {correct_id}')
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"Updated {file_path}: {current_id} -> {correct_id}")
                return True
            else:
                print(f"Already correct: {file_path}")
                return True
        else:
            print(f"Warning: No mapping found for {latin_name} in {file_path}")
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
    
    print("Loading genus mappings...")
    genus_mapping = load_genus_mapping(plants_file)
    print(f"Loaded {len(genus_mapping)} genus mappings")
    
    # Process all .md files in families directory
    md_files = list(families_dir.glob("*.tx.md"))
    print(f"Found {len(md_files)} .md files to process")
    
    updated_count = 0
    for md_file in md_files:
        if update_md_file(md_file, genus_mapping):
            updated_count += 1
    
    print(f"Successfully updated {updated_count}/{len(md_files)} files")
    return 0

if __name__ == "__main__":
    exit(main())
