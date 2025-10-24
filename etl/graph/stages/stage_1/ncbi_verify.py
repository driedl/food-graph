#!/usr/bin/env python3
"""
Stage 1: NCBI Verification

Computes parent relationships from taxon ID structure, verifies NCBI taxonomy IDs,
and enriches taxa with full lineage information for applicability matching.

Input: compiled/taxa.jsonl (from Stage 0)
Output: tmp/taxa_verified.jsonl
"""

from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

from graph.io import read_jsonl, write_jsonl, ensure_dir

def compute_parent_from_id(taxon_id: str) -> Optional[str]:
    """Compute parent taxon ID by dropping the last segment."""
    segments = taxon_id.split(':')
    if len(segments) <= 2:  # tx:p or tx:a (kingdom level)
        return None
    return ':'.join(segments[:-1])

def verify_ncbi_taxid(taxon: Dict[str, Any], ncbi_db: sqlite3.Connection) -> Dict[str, Any]:
    """Verify and enrich taxon with NCBI data."""
    taxon_id = taxon['id']
    rank = taxon.get('rank', '')
    ncbi_taxid = taxon.get('ncbi_taxid')
    latin_name = taxon.get('latin_name', '')
    
    result = taxon.copy()
    
    # Compute parent from ID structure
    result['parent'] = compute_parent_from_id(taxon_id)
    
    # If NCBI taxid exists, validate it
    if ncbi_taxid:
        cursor = ncbi_db.cursor()
        cursor.execute("SELECT taxid FROM ncbi_merged WHERE old_taxid = ?", (ncbi_taxid,))
        merged = cursor.fetchone()
        if merged:
            result['ncbi_taxid'] = merged[0]
            print(f"Updated merged taxid {ncbi_taxid} -> {merged[0]} for {taxon_id}")
    
    # If no NCBI taxid and rank <= species, try to find one
    if not result.get('ncbi_taxid') and rank in ['species', 'genus']:
        # Parse genus and species from latin_name
        name_parts = latin_name.split()
        if len(name_parts) >= 2:
            genus = name_parts[0]
            species = name_parts[1]
            scientific_name = f"{genus} {species}"
            
            # Query NCBI by scientific name
            cursor = ncbi_db.cursor()
            cursor.execute("""
                SELECT n.taxid, n.name_class 
                FROM ncbi_names n
                WHERE n.name_txt = ? AND n.name_class = 'scientific name'
                LIMIT 1
            """, (scientific_name,))
            
            match = cursor.fetchone()
            if match:
                result['ncbi_taxid'] = match[0]
                print(f"Found NCBI taxid {match[0]} for {taxon_id} ({scientific_name})")
            else:
                # Try genus-only fallback
                cursor.execute("""
                    SELECT n.taxid, n.name_class 
                    FROM ncbi_names n
                    WHERE n.name_txt = ? AND n.name_class = 'scientific name'
                    LIMIT 1
                """, (genus,))
                
                genus_match = cursor.fetchone()
                if genus_match:
                    result['ncbi_taxid'] = genus_match[0]
                    result['needs_refinement'] = True
                    print(f"Found genus-level NCBI taxid {genus_match[0]} for {taxon_id} ({genus})")
                else:
                    print(f"WARNING: No NCBI match for {taxon_id} ({scientific_name})")
    
    # Enrich with lineage if NCBI taxid exists
    if result.get('ncbi_taxid'):
        cursor = ncbi_db.cursor()
        cursor.execute("""
            SELECT kingdom, phylum, class, order_name, family, genus, species, lineage_json
            FROM ncbi_lineage 
            WHERE taxid = ?
        """, (result['ncbi_taxid'],))
        
        lineage_row = cursor.fetchone()
        if lineage_row:
            result['ncbi_lineage'] = {
                'kingdom': lineage_row[0],
                'phylum': lineage_row[1],
                'class': lineage_row[2],
                'order': lineage_row[3],
                'family': lineage_row[4],
                'genus': lineage_row[5],
                'species': lineage_row[6]
            }
            result['ncbi_lineage_json'] = lineage_row[7]
    
    return result

def complete_taxonomic_tree(taxa: List[Dict[str, Any]], ncbi_db: sqlite3.Connection, verbose: bool = False) -> List[Dict[str, Any]]:
    """Complete the taxonomic tree by adding missing intermediate nodes from NCBI."""
    # Create a set of existing taxon IDs
    existing_ids = {taxon['id'] for taxon in taxa}
    
    # For each taxon, walk up the hierarchy and add missing nodes
    all_taxa = taxa.copy()
    added_taxa = set()
    
    for taxon in taxa:
        current_id = taxon['id']
        
        # Walk up the hierarchy
        while True:
            parent_id = compute_parent_from_id(current_id)
            if not parent_id:
                break
                
            if parent_id not in existing_ids and parent_id not in added_taxa:
                # Create missing parent node from NCBI
                parent_taxon = create_parent_from_ncbi(parent_id, ncbi_db, verbose)
                if parent_taxon:
                    all_taxa.append(parent_taxon)
                    added_taxa.add(parent_id)
                    if verbose:
                        print(f"Added missing parent: {parent_id}")
            
            current_id = parent_id
    
    return all_taxa

def create_parent_from_ncbi(parent_id: str, ncbi_db: sqlite3.Connection, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """Create a parent taxon from NCBI data."""
    segments = parent_id.split(':')
    if len(segments) < 2:
        return None
    
    kingdom = segments[1]
    kingdom_name = {'p': 'Plantae', 'a': 'Animalia', 'f': 'Fungi'}.get(kingdom)
    if not kingdom_name:
        return None
    
    cursor = ncbi_db.cursor()
    
    if len(segments) == 2:
        # Kingdom level
        cursor.execute("""
            SELECT taxid FROM ncbi_lineage 
            WHERE kingdom = ? AND phylum IS NULL
            LIMIT 1
        """, (kingdom_name,))
    elif len(segments) == 3:
        # Genus level
        genus = segments[2]
        cursor.execute("""
            SELECT taxid FROM ncbi_lineage 
            WHERE kingdom = ? AND genus = ?
            LIMIT 1
        """, (kingdom_name, genus))
    else:
        # Higher level - would need more complex logic
        return None
    
    result = cursor.fetchone()
    if not result:
        return None
    
    taxid = result[0]
    
    # Get lineage data
    cursor.execute("""
        SELECT kingdom, phylum, class, order_name, family, genus, species, lineage_json
        FROM ncbi_lineage WHERE taxid = ?
    """, (taxid,))
    
    lineage_row = cursor.fetchone()
    if not lineage_row:
        return None
    
    # Determine rank and display name
    if len(segments) == 2:
        rank = 'kingdom'
        display_name = kingdom_name
        latin_name = kingdom_name
    elif len(segments) == 3:
        rank = 'genus'
        display_name = segments[2].title()
        latin_name = segments[2]
    else:
        return None
    
    return {
        'id': parent_id,
        'rank': rank,
        'display_name': display_name,
        'latin_name': latin_name,
        'aliases': [],
        'ncbi_taxid': taxid,
        'ncbi_lineage': {
            'kingdom': lineage_row[0],
            'phylum': lineage_row[1],
            'class': lineage_row[2],
            'order': lineage_row[3],
            'family': lineage_row[4],
            'genus': lineage_row[5],
            'species': lineage_row[6]
        },
        'ncbi_lineage_json': lineage_row[7]
    }

def verify_taxa(in_dir: Path, tmp_dir: Path, ncbi_db_path: Path, verbose: bool = False) -> None:
    """Main verification function."""
    ensure_dir(tmp_dir)
    
    # Load taxa from Stage 0
    taxa_path = in_dir / "compiled" / "taxa.jsonl"
    if not taxa_path.exists():
        raise FileNotFoundError(f"Input file not found: {taxa_path}")
    
    taxa = read_jsonl(taxa_path)
    if verbose:
        print(f"Loaded {len(taxa)} taxa from {taxa_path}")
    
    # Connect to NCBI database
    if not ncbi_db_path.exists():
        raise FileNotFoundError(f"NCBI database not found: {ncbi_db_path}")
    
    ncbi_db = sqlite3.connect(str(ncbi_db_path))
    
    try:
        # Verify each taxon
        verified_taxa = []
        for taxon in taxa:
            verified = verify_ncbi_taxid(taxon, ncbi_db)
            verified_taxa.append(verified)
        
        # Complete the taxonomic tree
        if verbose:
            print("Completing taxonomic tree...")
        complete_taxa = complete_taxonomic_tree(verified_taxa, ncbi_db, verbose)
        
        # Write verified taxa to compiled directory (overwrites Stage 0 output)
        output_path = tmp_dir.parent / "compiled" / "taxa.jsonl"
        write_jsonl(output_path, complete_taxa)
        
        if verbose:
            print(f"Verified {len(verified_taxa)} original taxa, added {len(complete_taxa) - len(verified_taxa)} missing nodes")
            print(f"Total: {len(complete_taxa)} taxa, wrote to {output_path}")
            
            # Print summary
            with_ncbi = sum(1 for t in complete_taxa if t.get('ncbi_taxid'))
            needs_refinement = sum(1 for t in complete_taxa if t.get('needs_refinement'))
            print(f"Summary: {with_ncbi} with NCBI taxid, {needs_refinement} need refinement")
    
    finally:
        ncbi_db.close()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Stage 1: NCBI Verification")
    parser.add_argument("--in-dir", type=Path, required=True, help="Input directory (build/)")
    parser.add_argument("--tmp-dir", type=Path, required=True, help="Temporary directory")
    parser.add_argument("--ncbi-db", type=Path, required=True, help="NCBI SQLite database path")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    verify_taxa(args.in_dir, args.tmp_dir, args.ncbi_db, args.verbose)

if __name__ == "__main__":
    main()
