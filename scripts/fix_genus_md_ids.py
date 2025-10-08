#!/usr/bin/env python3
"""
Fix plant .md file IDs to correctly map to genus level in plants_fixed_ids.jsonl.
The files describe individual genera, not families.
"""
import json
import re
from pathlib import Path

def load_genus_mapping(plants_file: Path) -> dict:
    """Load genus mappings from plants_fixed_ids.jsonl"""
    genera = {}
    
    with open(plants_file, 'r') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                if data['rank'] == 'genus':
                    id_parts = data['id'].split(':')
                    if len(id_parts) >= 6:
                        kingdom, clade, order, family, genus = id_parts[1:6]
                        # Create mapping from old format to new format
                        old_id = f"tx:{kingdom}:{clade}:{order}:{genus}"
                        new_id = f"tx:{kingdom}:{clade}:{order}:{family}:{genus}"
                        genera[old_id] = new_id
    
    return genera

def get_genus_from_filename(file_path: Path) -> str:
    """Extract genus name from filename patterns"""
    filename = file_path.stem
    
    # Extract genus from patterns like "Brassicaceae--arugula-rocket" -> "eruca"
    if '--' in filename:
        # Look for genus name in the description part
        desc_part = filename.split('--')[1]
        
        # Map common descriptions to genus names
        genus_mapping = {
            'arugula-rocket': 'eruca',
            'chickpeas-garbanzos': 'cicer',
            'soybeans': 'glycine',
            'lentils': 'lens',
            'peanuts-groundnuts': 'arachis',
            'mung-bean-cowpea-adzuki': 'vigna',
            'common-lima-runner-beans': 'phaseolus',
            'cabbages-mustards-rapeseed': 'brassica',
            'mustards': 'brassica',
            'apples': 'malus',
            'bananas-plantains': 'musa',
            'banana-family': 'musa',
            'lettuce': 'lactuca',
            'rye': 'secale',
            'pines-pine-nuts': 'pinus',
            'pine-family': 'pinus',
            'flax-linseed': 'linum',
            'flax-family': 'linum',
            'green-cardamom': 'elettaria',
            'spinach': 'spinacia',
            'cinnamon-cassia': 'cinnamomum',
            'blueberries-cranberries-huckleberries': 'vaccinium',
            'heath-family': 'ericaceae',  # This is actually family level
            'soybeans': 'glycine',
            'brazil-nut-family': 'bertholletia',
            'brazil-nuts': 'bertholletia',
            'beeches': 'castanea',
            'chestnuts': 'castanea',
            'walnut-family': 'juglans',
            'walnuts': 'juglans',
            'pecans-hickories': 'carya',
            'cucumbers-muskmelons': 'cucumis',
            'squashes-pumpkins': 'cucurbita',
            'gourds': 'cucurbita',
            'olive-family': 'olea',
            'olives-olive-oil': 'olea',
            'mint-family': 'salvia',
            'culinary-sages-chia': 'salvia',
            'tomatoes-potatoes-eggplants': 'solanum',
            'nightshade-family': 'solanaceae',  # This is family level
            'asparagus-family': 'asparagus',
            'asparagus': 'asparagus',
            'pepper-family': 'piper',
            'black-long-pepper-betel-leaf': 'piper',
            'celery': 'apium',
            'pineapples': 'ananas',
            'pineapple-family': 'ananas',
            'clove-rose-apples': 'syzygium',
            'myrtles': 'myrtaceae',  # This is family level
            'allspice-pimento': 'pimenta',
            'grapes': 'vitis',
            'sweet-potatoes-water-spinach': 'ipomoea',
            'morning-glory': 'convolvulaceae',  # This is family level
            'brambles': 'rubus',
            'pears': 'pyrus',
            'citrus': 'citrus',
            'lentils': 'lens',
            'rose-family': 'rosaceae',  # This is family level
            'asters': 'asteraceae',  # This is family level
            'cassava-manioc': 'manihot',
            'spurges': 'euphorbiaceae',  # This is family level
            'cashew-family': 'anacardium',
            'laurel-family': 'lauraceae',  # This is family level
            'buckwheat-rhubarb': 'fagopyrum',
            'pistachio': 'pistacia',
            'wheat': 'triticum',
            'strawberries': 'fragaria',
            'coconut': 'cocos',
            'carrot-family': 'daucus',
            'cumin': 'cuminum',
            'nutmeg-family': 'myristica',
            'nutmeg-mace': 'myristica',
            'amaranth-quinoa': 'chenopodium',
            'avocado': 'persea',
            'sesame': 'sesamum',
            'sesame-family': 'sesamum',
            'carrot': 'daucus',
            'buckwheat': 'fagopyrum',
            'pecans-hickories': 'carya',
            'sunflower': 'helianthus',
            'citrus-family': 'citrus',
            'rice': 'oryza',
            'pearl-millet': 'pennisetum',
            'olives-olive-oil': 'olea',
            'kiwifruit': 'actinidia',
            'onion': 'allium',
            'pawpaw': 'asimina',
            'cashew': 'anacardium',
            'groundcherries-tomatillos': 'physalis',
            'wild-rice': 'zizania',
            'stone-fruits-almonds': 'prunus'
        }
        
        return genus_mapping.get(desc_part, '')
    
    return ''

def update_md_file(file_path: Path, genus_mapping: dict) -> bool:
    """Update a single .md file with the correct genus ID"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the id field in frontmatter
        id_match = re.search(r'^id:\s*(.+)$', content, re.MULTILINE)
        if not id_match:
            print(f"Warning: No id field found in {file_path}")
            return False
            
        current_id = id_match.group(1).strip()
        
        # Get the genus name from filename
        genus_name = get_genus_from_filename(file_path)
        if not genus_name:
            print(f"Warning: Could not determine genus for {file_path}")
            return False
        
        # Find the correct genus ID
        # Extract the base path from current ID and add genus
        id_parts = current_id.split(':')
        if len(id_parts) >= 4:
            base_id = ':'.join(id_parts[:4])  # tx:plantae:clade:order
            old_genus_id = f"{base_id}:{genus_name}"
            
            if old_genus_id in genus_mapping:
                new_id = genus_mapping[old_genus_id]
                
                # Update the ID
                new_content = content.replace(f'id: {current_id}', f'id: {new_id}')
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"Updated {file_path}: {current_id} -> {new_id}")
                return True
            else:
                print(f"Warning: No mapping found for {old_genus_id} in {file_path}")
                return False
        else:
            print(f"Warning: Invalid ID format {current_id} in {file_path}")
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
