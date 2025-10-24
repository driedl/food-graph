#!/usr/bin/env python3
"""
Comprehensive taxon ID fixer that:
1. Fixes broken taxon IDs in plants file
2. Updates all rules files to use correct taxon IDs
3. Creates a mapping from old to new IDs
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

def parse_latin_name(latin_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse latin_name to extract genus, species, and variety."""
    name = latin_name.strip()
    
    # Handle variety patterns
    var_match = re.match(r'^(\w+)\s+(\w+)\s+var\.\s+(\w+)$', name)
    if var_match:
        genus, species, variety = var_match.groups()
        return genus.lower(), species.lower(), variety.lower()
    
    # Handle subspecies patterns
    ssp_match = re.match(r'^(\w+)\s+(\w+)\s+ssp\.\s+(\w+)$', name)
    if ssp_match:
        genus, species, subspecies = ssp_match.groups()
        return genus.lower(), species.lower(), subspecies.lower()
    
    # Handle simple genus species
    simple_match = re.match(r'^(\w+)\s+(\w+)$', name)
    if simple_match:
        genus, species = simple_match.groups()
        return genus.lower(), species.lower(), None
    
    # Handle single word (genus only)
    if re.match(r'^\w+$', name):
        return name.lower(), None, None
    
    return None, None, None

def create_taxon_id(kingdom: str, genus: str, species: Optional[str] = None, variety: Optional[str] = None) -> str:
    """Create proper taxon ID from components."""
    parts = [f"tx:{kingdom}", genus]
    if species:
        parts.append(species)
    if variety:
        parts.append(variety)
    return ":".join(parts)

def fix_plants_file(file_path: Path) -> Dict[str, str]:
    """Fix plants file and return mapping of old_id -> new_id."""
    print(f"Processing {file_path}")
    
    # Read all taxa
    taxa = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('//'):
                taxa.append(json.loads(line))
    
    # Process taxa and build hierarchy
    processed_taxa = []
    seen_ids: Set[str] = set()
    id_mapping: Dict[str, str] = {}
    
    for taxon in taxa:
        old_id = taxon.get('id', '')
        latin_name = taxon.get('latin_name', '')
        rank = taxon.get('rank', '')
        
        # Parse latin name
        genus, species, variety = parse_latin_name(latin_name)
        
        if not genus:
            print(f"WARNING: Could not parse latin_name '{latin_name}' in {old_id}")
            continue
        
        # Create proper ID
        if variety:
            new_id = create_taxon_id("p", genus, species, variety)
            new_rank = 'variety'
        elif species:
            new_id = create_taxon_id("p", genus, species)
            new_rank = 'species'
        else:
            # Genus only - keep genus-level taxa for documentation
            new_id = create_taxon_id("p", genus)
            new_rank = 'genus'
        
        # Check for duplicates
        if new_id in seen_ids:
            print(f"WARNING: Duplicate ID {new_id} for {latin_name}")
            continue
        
        seen_ids.add(new_id)
        
        # Create mapping
        if old_id != new_id:
            id_mapping[old_id] = new_id
        
        # Create new taxon entry
        new_taxon = {
            'id': new_id,
            'rank': new_rank,
            'display_name': taxon.get('display_name', ''),
            'latin_name': latin_name,
            'aliases': taxon.get('aliases', [])
        }
        
        # Add NCBI taxid if present
        if 'ncbi_taxid' in taxon:
            new_taxon['ncbi_taxid'] = taxon['ncbi_taxid']
        
        processed_taxa.append(new_taxon)
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        for taxon in processed_taxa:
            f.write(json.dumps(taxon, ensure_ascii=False) + '\n')
    
    print(f"Fixed {len(processed_taxa)} taxa in {file_path}")
    print(f"Created {len(id_mapping)} ID mappings")
    return id_mapping

def update_jsonl_file(file_path: Path, id_mapping: Dict[str, str]) -> int:
    """Update a JSONL file with new taxon IDs."""
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
                    if isinstance(value, str) and value.startswith('tx:p:'):
                        if value in id_mapping:
                            data[key] = id_mapping[value]
                            updated = True
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            if isinstance(item, str) and item.startswith('tx:p:'):
                                if item in id_mapping:
                                    data[key][i] = id_mapping[item]
                                    updated = True
                
                if updated:
                    updated_count += 1
                
                outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
                
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON in {file_path}:{line_num}: {e}")
                outfile.write(line + '\n')
    
    if updated_count > 0:
        temp_file.replace(file_path)
        print(f"Updated {updated_count} entries in {file_path}")
    else:
        temp_file.unlink()
    
    return updated_count

def update_json_file(file_path: Path, id_mapping: Dict[str, str]) -> int:
    """Update a JSON file with new taxon IDs."""
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
                    if isinstance(value, str) and value.startswith('tx:p:'):
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
        
        if updated_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Updated {updated_count} entries in {file_path}")
        
        return updated_count
        
    except Exception as e:
        print(f"ERROR: Failed to process {file_path}: {e}")
        return 0

def main():
    """Fix all taxon files and update rules."""
    ontology_dir = Path("data/ontology")
    rules_dir = ontology_dir / "rules"
    
    # Fix plants file and get ID mapping
    plants_file = ontology_dir / "taxa" / "plantae" / "plants_fixed_ids.jsonl"
    if not plants_file.exists():
        print(f"ERROR: Plants file not found: {plants_file}")
        return
    
    id_mapping = fix_plants_file(plants_file)
    
    if not id_mapping:
        print("No ID mappings needed - plants file was already correct")
        return
    
    print(f"\nUpdating rules files with {len(id_mapping)} ID mappings...")
    
    # Update all rules files
    rules_files = [
        "derived_foods.jsonl",
        "name_overrides.jsonl", 
        "taxon_part_synonyms.jsonl",
        "parts_applicability.jsonl",
        "implied_parts.jsonl",
        "promoted_parts.jsonl",
        "transform_applicability.jsonl",
        "diet_safety_rules.jsonl",
        "family_allowlist.jsonl",
        "cuisine_map.jsonl"
    ]
    
    total_updates = 0
    for filename in rules_files:
        file_path = rules_dir / filename
        if file_path.exists():
            updates = update_jsonl_file(file_path, id_mapping)
            total_updates += updates
    
    # Update JSON files
    json_files = [
        "taxon_part_policy.json",
        "family_recipes.json"
    ]
    
    for filename in json_files:
        file_path = rules_dir / filename
        if file_path.exists():
            updates = update_json_file(file_path, id_mapping)
            total_updates += updates
    
    print(f"\nTotal updates across all files: {total_updates}")
    print("Taxon ID fixing complete!")

if __name__ == "__main__":
    main()
