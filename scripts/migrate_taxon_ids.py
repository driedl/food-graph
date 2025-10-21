#!/usr/bin/env python3
"""
One-time Taxon ID Migration Script

Converts all taxon IDs from full rank ladder format to kingdom-genus-species format.

Rules:
- Kingdom: plantae→p, animalia→a, fungi→f
- Keep: genus, species, cultivar/variety/breed
- Drop: clade, order, family, class, phylum

Usage:
    python scripts/migrate_taxon_ids.py
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

def migrate_taxon_id(old_id: str) -> str:
    """Convert old taxon ID to new format."""
    if not old_id.startswith('tx:'):
        return old_id
    
    segments = old_id.split(':')
    if len(segments) < 3:
        return old_id
    
    # Extract kingdom
    kingdom = segments[1]
    kingdom_map = {
        'plantae': 'p',
        'animalia': 'a', 
        'fungi': 'f'
    }
    
    if kingdom not in kingdom_map:
        print(f"WARNING: Unknown kingdom '{kingdom}' in {old_id}")
        return old_id
    
    new_segments = ['tx', kingdom_map[kingdom]]
    
    # Find genus, species, and below-species ranks
    genus_idx = None
    species_idx = None
    
    # Look for genus (usually 2-3 segments from end)
    for i in range(len(segments) - 1, max(1, len(segments) - 4), -1):
        if segments[i] and not segments[i] in ['eukaryota', 'plantae', 'animalia', 'fungi']:
            # Check if this looks like a genus (single word, not a rank)
            if not segments[i] in ['eudicots', 'monocots', 'gymnosperms', 'chordata', 'arthropoda', 'mollusca']:
                genus_idx = i
                break
    
    if genus_idx is None:
        print(f"WARNING: Could not find genus in {old_id}")
        return old_id
    
    # Add genus
    new_segments.append(segments[genus_idx])
    
    # Look for species (next segment after genus)
    if genus_idx + 1 < len(segments):
        species_idx = genus_idx + 1
        new_segments.append(segments[species_idx])
        
        # Add any below-species ranks (cultivar, variety, breed)
        for i in range(species_idx + 1, len(segments)):
            if segments[i]:
                new_segments.append(segments[i])
    
    return ':'.join(new_segments)

def migrate_taxa_file(file_path: Path, id_mapping: Dict[str, str]) -> int:
    """Migrate a single taxa JSONL file."""
    print(f"Migrating {file_path}")
    
    migrated_count = 0
    taxa = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                taxon = json.loads(line)
                old_id = taxon.get('id', '')
                
                if old_id.startswith('tx:'):
                    new_id = migrate_taxon_id(old_id)
                    if new_id != old_id:
                        taxon['id'] = new_id
                        id_mapping[old_id] = new_id
                        migrated_count += 1
                        
                        # Remove parent field if present (will be computed)
                        if 'parent' in taxon:
                            del taxon['parent']
                
                taxa.append(taxon)
                
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON in {file_path}:{line_num}: {e}")
                continue
    
    # Write back the migrated file
    with open(file_path, 'w', encoding='utf-8') as f:
        for taxon in taxa:
            f.write(json.dumps(taxon, ensure_ascii=False) + '\n')
    
    print(f"  Migrated {migrated_count} taxon IDs")
    return migrated_count

def migrate_rules_file(file_path: Path, id_mapping: Dict[str, str]) -> int:
    """Migrate a rules JSONL file that may contain taxon IDs."""
    print(f"Migrating rules file {file_path}")
    
    migrated_count = 0
    rules = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                rule = json.loads(line)
                rule_migrated = False
                
                # Check various fields that might contain taxon IDs
                for field in ['applies_to', 'taxon_prefix', 'taxon_id']:
                    if field in rule:
                        if isinstance(rule[field], str):
                            old_id = rule[field]
                            if old_id.startswith('tx:'):
                                new_id = migrate_taxon_id(old_id)
                                if new_id != old_id:
                                    rule[field] = new_id
                                    id_mapping[old_id] = new_id
                                    rule_migrated = True
                        elif isinstance(rule[field], list):
                            for i, item in enumerate(rule[field]):
                                if isinstance(item, str) and item.startswith('tx:'):
                                    new_id = migrate_taxon_id(item)
                                    if new_id != item:
                                        rule[field][i] = new_id
                                        id_mapping[item] = new_id
                                        rule_migrated = True
                
                if rule_migrated:
                    migrated_count += 1
                
                rules.append(rule)
                
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON in {file_path}:{line_num}: {e}")
                continue
    
    # Write back the migrated file
    with open(file_path, 'w', encoding='utf-8') as f:
        for rule in rules:
            f.write(json.dumps(rule, ensure_ascii=False) + '\n')
    
    print(f"  Migrated {migrated_count} rules")
    return migrated_count

def main():
    """Main migration function."""
    ontology_dir = Path("data/ontology")
    
    if not ontology_dir.exists():
        print(f"ERROR: Ontology directory not found: {ontology_dir}")
        return
    
    id_mapping = {}
    total_migrated = 0
    
    # Migrate taxa files
    taxa_files = [
        ontology_dir / "taxa" / "index.jsonl",
        ontology_dir / "taxa" / "plantae" / "plants_fixed_ids.jsonl",
        ontology_dir / "taxa" / "animalia" / "animals.jsonl",
        ontology_dir / "taxa" / "fungi" / "fungi.jsonl"
    ]
    
    for taxa_file in taxa_files:
        if taxa_file.exists():
            total_migrated += migrate_taxa_file(taxa_file, id_mapping)
        else:
            print(f"WARNING: Taxa file not found: {taxa_file}")
    
    # Migrate rules files
    rules_dir = ontology_dir / "rules"
    if rules_dir.exists():
        for rules_file in rules_dir.glob("*.jsonl"):
            total_migrated += migrate_rules_file(rules_file, id_mapping)
    
    # Write mapping for validation
    mapping_path = Path("tmp/taxon_id_mapping.json")
    mapping_path.parent.mkdir(exist_ok=True)
    
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(id_mapping, f, indent=2, ensure_ascii=False)
    
    print(f"\nMigration complete!")
    print(f"Total IDs migrated: {total_migrated}")
    print(f"ID mapping saved to: {mapping_path}")
    
    # Print some examples
    print(f"\nExample migrations:")
    for i, (old_id, new_id) in enumerate(list(id_mapping.items())[:5]):
        print(f"  {old_id} -> {new_id}")
    
    if len(id_mapping) > 5:
        print(f"  ... and {len(id_mapping) - 5} more")

if __name__ == "__main__":
    main()
