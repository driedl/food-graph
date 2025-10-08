#!/usr/bin/env python3
"""
Fix plant .md file IDs to match the correct family structure from plants_fixed_ids.jsonl.
This script creates a more accurate mapping based on the actual family names in the file names.
"""
import json
import re
from pathlib import Path

def load_family_mapping(plants_file: Path) -> dict:
    """Load family mappings from plants_fixed_ids.jsonl"""
    families = {}
    
    with open(plants_file, 'r') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                if data['rank'] == 'family':
                    id_parts = data['id'].split(':')
                    if len(id_parts) >= 5:
                        kingdom, clade, order, family = id_parts[1:5]
                        families[family] = data['id']
    
    return families

def get_correct_family_id(file_path: Path, families: dict) -> str:
    """Determine the correct family ID based on the file name"""
    filename = file_path.stem
    
    # Extract family name from filename patterns
    if '--' in filename:
        family_part = filename.split('--')[0]
    else:
        family_part = filename
    
    # Map common family name variations
    family_mapping = {
        'Amaryllidaceae': 'amaryllidaceae',
        'Asparagaceae': 'asparagaceae', 
        'Actinidiaceae': 'actinidiaceae',
        'Ericaceae': 'ericaceae',
        'Lecythidaceae': 'lecythidaceae',
        'Betulaceae': 'betulaceae',
        'Fagaceae': 'fagaceae',
        'Juglandaceae': 'juglandaceae',
        'Linaceae': 'linaceae',
        'Euphorbiaceae': 'euphorbiaceae',
        'Myristicaceae': 'myristicaceae',
        'Pedaliaceae': 'pedaliaceae',
        'Lamiaceae': 'lamiaceae',
        'Oleaceae': 'oleaceae',
        'Pinaceae': 'pinaceae',
        'Piperaceae': 'piperaceae',
        'Poaceae': 'poaceae',
        'Polygonaceae': 'polygonaceae',
        'Proteaceae': 'proteaceae',
        'Rosaceae': 'rosaceae',
        'Rutaceae': 'rutaceae',
        'Solanaceae': 'solanaceae',
        'Vitaceae': 'vitaceae',
        'Zingiberaceae': 'zingiberaceae',
        'Musaceae': 'musaceae',
        'Arecaceae': 'arecaceae',
        'Bromeliaceae': 'bromeliaceae',
        'Amaranthaceae': 'amaranthaceae',
        'Anacardiaceae': 'anacardiaceae',
        'Annonaceae': 'annonaceae',
        'Apiaceae': 'apiaceae',
        'Asteraceae': 'asteraceae',
        'Brassicaceae': 'brassicaceae',
        'Convolvulaceae': 'convolvulaceae',
        'Cucurbitaceae': 'cucurbitaceae',
        'Fabaceae': 'fabaceae',
        'Lauraceae': 'lauraceae',
        'Myrtaceae': 'myrtaceae'
    }
    
    family_name = family_mapping.get(family_part, family_part.lower())
    return families.get(family_name, '')

def update_md_file(file_path: Path, families: dict) -> bool:
    """Update a single .md file with the correct family ID"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the id field in frontmatter
        id_match = re.search(r'^id:\s*(.+)$', content, re.MULTILINE)
        if not id_match:
            print(f"Warning: No id field found in {file_path}")
            return False
            
        current_id = id_match.group(1).strip()
        
        # Get the correct family ID
        correct_family_id = get_correct_family_id(file_path, families)
        if not correct_family_id:
            print(f"Warning: Could not determine correct family for {file_path}")
            return False
        
        # Update the ID
        new_content = content.replace(f'id: {current_id}', f'id: {correct_family_id}')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Updated {file_path}: {current_id} -> {correct_family_id}")
        return True
        
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
    
    print("Loading family mappings...")
    families = load_family_mapping(plants_file)
    print(f"Loaded {len(families)} family mappings")
    
    # Process all .md files in families directory
    md_files = list(families_dir.glob("*.tx.md"))
    print(f"Found {len(md_files)} .md files to process")
    
    updated_count = 0
    for md_file in md_files:
        if update_md_file(md_file, families):
            updated_count += 1
    
    print(f"Successfully updated {updated_count}/{len(md_files)} files")
    return 0

if __name__ == "__main__":
    exit(main())
