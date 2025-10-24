#!/usr/bin/env python3
"""
Update ontology files with NCBI taxon IDs from Stage 1 output.

This script reads the compiled taxa.jsonl from Stage 1 and updates the original
ontology files with the NCBI taxon IDs that were found.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

def read_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Read a JSONL file and return list of objects."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data

def update_taxa_file(file_path: Path, ncbi_mappings: Dict[str, int]) -> int:
    """Update a taxa JSONL file with NCBI taxon IDs."""
    updated_count = 0
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Update lines that have matching taxon IDs
    updated_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            updated_lines.append(line)
            continue
            
        try:
            taxon = json.loads(line)
            taxon_id = taxon.get('id')
            
            if taxon_id in ncbi_mappings:
                # Add or update ncbi_taxid field
                taxon['ncbi_taxid'] = ncbi_mappings[taxon_id]
                updated_count += 1
                print(f"Updated {taxon_id} with NCBI taxon ID {ncbi_mappings[taxon_id]}")
            
            updated_lines.append(json.dumps(taxon, ensure_ascii=False))
        except json.JSONDecodeError:
            # Keep non-JSON lines as-is
            updated_lines.append(line)
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        for line in updated_lines:
            f.write(line + '\n')
    
    return updated_count

def main():
    # Paths
    etl_dir = Path(__file__).parent.parent
    compiled_taxa_path = etl_dir / "build" / "compiled" / "taxa.jsonl"
    ontology_dir = Path(__file__).parent.parent.parent / "data" / "ontology" / "taxa"
    
    if not compiled_taxa_path.exists():
        print(f"ERROR: Compiled taxa file not found: {compiled_taxa_path}")
        print("Please run Stage 1 first: python -m graph run 1")
        sys.exit(1)
    
    # Load NCBI mappings from compiled taxa
    print("Loading NCBI taxon ID mappings from Stage 1 output...")
    compiled_taxa = read_jsonl(compiled_taxa_path)
    
    ncbi_mappings = {}
    for taxon in compiled_taxa:
        if 'ncbi_taxid' in taxon:
            ncbi_mappings[taxon['id']] = taxon['ncbi_taxid']
    
    print(f"Found {len(ncbi_mappings)} taxa with NCBI taxon IDs")
    
    if not ncbi_mappings:
        print("No NCBI taxon IDs found. Nothing to update.")
        sys.exit(0)
    
    # Update all taxa files
    total_updated = 0
    taxa_files = list(ontology_dir.glob("**/*.jsonl"))
    
    for taxa_file in taxa_files:
        print(f"Updating {taxa_file.relative_to(ontology_dir)}...")
        updated = update_taxa_file(taxa_file, ncbi_mappings)
        total_updated += updated
        print(f"  Updated {updated} taxa")
    
    print(f"\nTotal: Updated {total_updated} taxa across {len(taxa_files)} files")
    print("\nNext steps:")
    print("1. Review the changes: git diff")
    print("2. Commit the updated ontology files: git add data/ontology/taxa/ && git commit -m 'Add NCBI taxon IDs to ontology'")
    print("3. Future ETL runs will be much faster since NCBI IDs are now stored in the ontology")

if __name__ == "__main__":
    main()
