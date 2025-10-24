#!/usr/bin/env python3
"""
Fix taxon IDs by reconstructing proper taxonomic hierarchy from latin_name.

This script fixes the incorrectly migrated taxon IDs by:
1. Parsing latin_name to extract genus and species
2. Reconstructing proper IDs in format tx:p:genus:species[:variety]
3. Only keeping leaf nodes (species/varieties) - removing intermediate ranks
4. Ensuring no duplicate IDs
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

def parse_latin_name(latin_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse latin_name to extract genus, species, and variety.
    
    Examples:
    - "Apium graveolens" -> ("apium", "graveolens", None)
    - "Brassica oleracea var. capitata" -> ("brassica", "oleracea", "capitata")
    - "Lactuca sativa var. longifolia" -> ("lactuca", "sativa", "longifolia")
    """
    # Clean up the name
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

def fix_taxon_file(file_path: Path, kingdom: str) -> None:
    """Fix taxon IDs in a single file."""
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
    
    for taxon in taxa:
        latin_name = taxon.get('latin_name', '')
        rank = taxon.get('rank', '')
        
        # Parse latin name
        genus, species, variety = parse_latin_name(latin_name)
        
        if not genus:
            print(f"WARNING: Could not parse latin_name '{latin_name}' in {taxon.get('id', 'unknown')}")
            continue
        
        # Create proper ID
        if variety:
            new_id = create_taxon_id(kingdom, genus, species, variety)
            new_rank = 'variety'
        elif species:
            new_id = create_taxon_id(kingdom, genus, species)
            new_rank = 'species'
        else:
            # Genus only - skip intermediate ranks
            continue
        
        # Check for duplicates
        if new_id in seen_ids:
            print(f"WARNING: Duplicate ID {new_id} for {latin_name}")
            continue
        
        seen_ids.add(new_id)
        
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

def main():
    """Fix all taxon files."""
    ontology_dir = Path("data/ontology/taxa")
    
    # Fix plants
    plants_file = ontology_dir / "plantae" / "plants_fixed_ids.jsonl"
    if plants_file.exists():
        fix_taxon_file(plants_file, "p")
    
    # Fix animals
    animals_file = ontology_dir / "animalia" / "animals.jsonl"
    if animals_file.exists():
        fix_taxon_file(animals_file, "a")
    
    # Fix fungi
    fungi_file = ontology_dir / "fungi" / "fungi.jsonl"
    if fungi_file.exists():
        fix_taxon_file(fungi_file, "f")
    
    print("Taxon ID fixing complete!")

if __name__ == "__main__":
    main()
