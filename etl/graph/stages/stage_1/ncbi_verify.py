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

def verify_ncbi_taxid_optimized(taxon: Dict[str, Any], merged_mappings: Dict[int, int], scientific_name_mappings: Dict[str, int]) -> Dict[str, Any]:
    """Optimized NCBI taxon ID verification using pre-loaded mappings."""
    taxon_id = taxon['id']
    ncbi_taxid = taxon.get('ncbi_taxid')
    rank = taxon.get('rank', '')
    latin_name = taxon.get('latin_name', '')
    
    result = taxon.copy()
    result['parent'] = compute_parent_from_id(taxon_id)
    
    # If NCBI taxid exists, check if it's been merged
    if ncbi_taxid:
        if ncbi_taxid in merged_mappings:
            new_taxid = merged_mappings[ncbi_taxid]
            result['ncbi_taxid'] = new_taxid
            result['_debug'] = f"merged {ncbi_taxid} -> {new_taxid}"
        else:
            result['ncbi_taxid'] = ncbi_taxid
            result['_debug'] = "existing"
    
    # If no NCBI taxid and rank <= species, try to find one
    if not result.get('ncbi_taxid') and rank in ['species', 'genus']:
        # Parse genus and species from latin_name
        name_parts = latin_name.split()
        if len(name_parts) >= 2:
            genus = name_parts[0]
            species = name_parts[1]
            scientific_name = f"{genus} {species}"
            
            # Look up in pre-loaded scientific name mappings
            if scientific_name in scientific_name_mappings:
                result['ncbi_taxid'] = scientific_name_mappings[scientific_name]
                result['_debug'] = f"found {scientific_name}"
            else:
                result['_debug'] = f"not found {scientific_name}"
        else:
            result['_debug'] = f"invalid name format: {latin_name}"
    
    return result

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
        cursor.execute("SELECT new_taxid FROM ncbi_merged WHERE old_taxid = ?", (ncbi_taxid,))
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

def complete_taxonomic_tree_with_ncbi_hierarchy(taxa: List[Dict[str, Any]], parent_relationships: Dict[int, Dict[str, Any]], ncbi_db: sqlite3.Connection, verbose: bool = False) -> List[Dict[str, Any]]:
    """Complete the taxonomic tree by walking up NCBI parent relationships."""
    # Create a set of existing taxon IDs
    existing_ids = {taxon['id'] for taxon in taxa}
    
    # For each taxon with NCBI taxid, walk up the hierarchy
    all_taxa = taxa.copy()
    added_taxa = set()
    
    for taxon in taxa:
        ncbi_taxid = taxon.get('ncbi_taxid')
        
        if ncbi_taxid:
            # Walk up the NCBI hierarchy and create missing intermediate nodes
            hierarchy_nodes = walk_ncbi_hierarchy(ncbi_taxid, ncbi_db, verbose)
            
            # Add hierarchy nodes in reverse order (kingdom first, then phylum, etc.)
            # This ensures parents are added before children
            for node_data in reversed(hierarchy_nodes):
                # Convert NCBI taxid to our taxon ID format
                our_taxon_id = ncbi_taxid_to_our_id(node_data['taxid'], node_data['rank'], node_data['name'], node_data['kingdom'])
                
                if our_taxon_id and our_taxon_id not in existing_ids and our_taxon_id not in added_taxa:
                    # Create the intermediate node
                    intermediate_node = {
                        'id': our_taxon_id,
                        'name': node_data['name'],
                        'rank': map_ncbi_rank_to_our_rank(node_data['rank']),
                        'display_name': node_data['name'],
                        'latin_name': node_data['name'],
                        'ncbi_taxid': node_data['taxid'],
                        'parent': ncbi_taxid_to_our_id(node_data['parent_taxid'], node_data['parent_rank'], node_data['parent_name'], node_data['kingdom']) if node_data['parent_taxid'] else None
                    }
                    
                    all_taxa.append(intermediate_node)
                    added_taxa.add(our_taxon_id)
                    
                    # Don't print individual nodes - we'll summarize at the end
        else:
            # For taxa without NCBI IDs, create missing parents using basic logic
            current_id = taxon['id']
            
            # Walk up the hierarchy and create missing parents
            while True:
                parent_id = compute_parent_from_id(current_id)
                if not parent_id:
                    break
                    
                if parent_id not in existing_ids and parent_id not in added_taxa:
                    # Create basic parent node
                    parent_taxon = create_basic_parent_node(parent_id, verbose)
                    if parent_taxon:
                        all_taxa.append(parent_taxon)
                        added_taxa.add(parent_id)
                        if verbose:
                            print(f"Added basic parent node: {parent_id}")
                
                current_id = parent_id
    
    # Create missing parents for taxa that reference non-existent parents
    def create_missing_parents(taxa_list):
        """Create missing parent nodes for taxa that reference non-existent parents."""
        taxa_map = {taxon['id']: taxon for taxon in taxa_list}
        added_parents = set()
        
        for taxon in taxa_list:
            parent_id = taxon.get('parent')
            if parent_id and parent_id not in taxa_map and parent_id not in added_parents:
                # Create the missing parent
                parent_taxon = create_basic_parent_node(parent_id, verbose)
                if parent_taxon:
                    taxa_list.append(parent_taxon)
                    taxa_map[parent_id] = parent_taxon
                    added_parents.add(parent_id)
                    if verbose:
                        print(f"Created missing parent: {parent_id}")
        
        return taxa_list
    
    # Create missing parents first
    all_taxa = create_missing_parents(all_taxa)
    
    # Sort all taxa to ensure parents are inserted before children
    def topological_sort(taxa_list):
        """Sort taxa so that parents come before children."""
        # Create a mapping of taxon ID to taxon data
        taxa_map = {taxon['id']: taxon for taxon in taxa_list}
        
        # Build dependency graph: child -> parent
        dependencies = {}
        for taxon in taxa_list:
            parent = taxon.get('parent')
            if parent and parent in taxa_map:
                dependencies[taxon['id']] = parent
        
        # Topological sort using Kahn's algorithm
        result = []
        in_degree = {taxon_id: 0 for taxon_id in taxa_map.keys()}
        
        # Calculate in-degrees
        for child, parent in dependencies.items():
            in_degree[child] += 1
        
        # Find all nodes with no dependencies (root nodes)
        queue = [taxon_id for taxon_id, degree in in_degree.items() if degree == 0]
        
        while queue:
            # Sort queue to ensure consistent ordering
            queue.sort()
            current = queue.pop(0)
            result.append(taxa_map[current])
            
            # Remove this node and update dependencies
            for child, parent in dependencies.items():
                if parent == current:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        queue.append(child)
        
        return result
    
    result = topological_sort(all_taxa)
    
    if verbose and added_taxa:
        print(f"Added {len(added_taxa)} NCBI hierarchy nodes to complete taxonomic tree")
    
    return result

def walk_ncbi_hierarchy(start_taxid: int, ncbi_db: sqlite3.Connection, verbose: bool = False) -> List[Dict[str, Any]]:
    """Walk up the NCBI hierarchy from a given taxid to kingdom level."""
    hierarchy = []
    current_taxid = start_taxid
    visited = set()
    kingdom = None
    
    while current_taxid and current_taxid not in visited:
        visited.add(current_taxid)
        
        # Get current node info
        cursor = ncbi_db.cursor()
        cursor.execute("""
            SELECT n.taxid, n.parent_taxid, n.rank, names.name_txt
            FROM ncbi_nodes n
            JOIN ncbi_names names ON n.taxid = names.taxid
            WHERE n.taxid = ? AND names.name_class = 'scientific name'
        """, (current_taxid,))
        
        row = cursor.fetchone()
        if not row:
            break
            
        taxid, parent_taxid, rank, name = row
        
        # Track kingdom when we find it
        if rank == 'kingdom':
            kingdom = name
        
        # Get parent info for the hierarchy
        parent_rank = None
        parent_name = None
        if parent_taxid:
            cursor.execute("""
                SELECT n.rank, names.name_txt
                FROM ncbi_nodes n
                JOIN ncbi_names names ON n.taxid = names.taxid
                WHERE n.taxid = ? AND names.name_class = 'scientific name'
            """, (parent_taxid,))
            parent_row = cursor.fetchone()
            if parent_row:
                parent_rank, parent_name = parent_row
        
        hierarchy.append({
            'taxid': taxid,
            'parent_taxid': parent_taxid,
            'rank': rank,
            'name': name,
            'parent_rank': parent_rank,
            'parent_name': parent_name,
            'kingdom': kingdom
        })
        
        # Stop at kingdom level or if no parent
        if rank == 'kingdom' or not parent_taxid:
            break
            
        current_taxid = parent_taxid
    
    return hierarchy

def ncbi_taxid_to_our_id(taxid: int, rank: str, name: str, kingdom: str = None) -> Optional[str]:
    """Convert NCBI taxid to our taxon ID format."""
    # Map kingdom names to our codes (NCBI uses different names)
    kingdom_code_map = {
        'Plantae': 'p', 
        'Viridiplantae': 'p',  # NCBI uses Viridiplantae
        'Animalia': 'a', 
        'Fungi': 'f',
        'Metazoa': 'a'  # NCBI sometimes uses Metazoa for animals
    }
    
    # Determine kingdom code
    if kingdom:
        kingdom_code = kingdom_code_map.get(kingdom, 'p')
    else:
        kingdom_code = 'p'  # Default fallback
    
    # Convert name to our format (lowercase, underscores)
    formatted_name = name.lower().replace(' ', '_')
    
    if rank == 'kingdom':
        return f"tx:{kingdom_code}"
    elif rank in ['phylum', 'class', 'order', 'family', 'genus']:
        return f"tx:{kingdom_code}:{formatted_name}"
    elif rank == 'species':
        # For species, we need the genus name too - this is complex
        # For now, just use the species name
        return f"tx:{kingdom_code}:{formatted_name}"
    
    return None

def map_ncbi_rank_to_our_rank(ncbi_rank: str) -> str:
    """Map NCBI rank to our taxonomic rank system."""
    rank_map = {
        'kingdom': 'kingdom',
        'phylum': 'phylum', 
        'class': 'class',
        'order': 'order',
        'family': 'family',
        'genus': 'genus',
        'species': 'species',
        'subspecies': 'species',
        'variety': 'species',
        'clade': 'class',  # Map clades to class level
        'superkingdom': 'kingdom'
    }
    return rank_map.get(ncbi_rank, 'unknown')

def complete_taxonomic_tree_optimized(taxa: List[Dict[str, Any]], lineage_data: Dict[int, Dict[str, Any]], verbose: bool = False) -> List[Dict[str, Any]]:
    """Complete the taxonomic tree by adding missing intermediate nodes."""
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
                # Create missing parent node - try NCBI first, then fallback to basic creation
                parent_taxon = create_parent_from_ncbi_optimized(parent_id, lineage_data, verbose)
                if not parent_taxon:
                    # Fallback: create basic parent node without NCBI data
                    parent_taxon = create_basic_parent_node(parent_id, verbose)
                
                if parent_taxon:
                    all_taxa.append(parent_taxon)
                    added_taxa.add(parent_id)
                    if verbose:
                        print(f"Added missing parent: {parent_id}")
            
            current_id = parent_id
    
    return all_taxa

def create_basic_parent_node(parent_id: str, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """Create a basic parent node without NCBI data when NCBI lookup fails."""
    segments = parent_id.split(':')
    if len(segments) < 2:
        return None
    
    kingdom = segments[1]
    kingdom_name = {'p': 'Plantae', 'a': 'Animalia', 'f': 'Fungi'}.get(kingdom)
    if not kingdom_name:
        return None
    
    # Determine rank and name based on hierarchy depth
    if len(segments) == 2:
        # Kingdom level
        rank = 'kingdom'
        name = kingdom_name
    elif len(segments) == 3:
        # Phylum level
        rank = 'phylum'
        name = segments[2].replace('_', ' ').title()
    elif len(segments) == 4:
        # Class level
        rank = 'class'
        name = segments[3].replace('_', ' ').title()
    elif len(segments) == 5:
        # Order level
        rank = 'order'
        name = segments[4].replace('_', ' ').title()
    elif len(segments) == 6:
        # Family level
        rank = 'family'
        name = segments[5].replace('_', ' ').title()
    elif len(segments) == 7:
        # Genus level
        rank = 'genus'
        name = segments[6].replace('_', ' ').title()
    else:
        return None
    
    return {
        'id': parent_id,
        'name': name,
        'rank': rank,
        'display_name': name,
        'latin_name': name,
        'parent': compute_parent_from_id(parent_id)
    }

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

def create_parent_from_ncbi_optimized(parent_id: str, lineage_data: Dict[int, Dict[str, Any]], verbose: bool = False) -> Optional[Dict[str, Any]]:
    """Create a parent taxon from pre-loaded NCBI data."""
    segments = parent_id.split(':')
    if len(segments) < 2:
        return None
    
    kingdom = segments[1]
    kingdom_name = {'p': 'Plantae', 'a': 'Animalia', 'f': 'Fungi'}.get(kingdom)
    if not kingdom_name:
        return None
    
    # Find matching NCBI taxon by searching through pre-loaded lineage data
    target_taxon = None
    
    if len(segments) == 2:
        # Kingdom level - find kingdom with no phylum
        for taxid, lineage in lineage_data.items():
            if lineage.get('kingdom') == kingdom_name and lineage.get('phylum') is None:
                target_taxon = (taxid, lineage)
                break
    elif len(segments) == 3:
        # Phylum level
        phylum_name = segments[2].replace('_', ' ')
        for taxid, lineage in lineage_data.items():
            if (lineage.get('kingdom') == kingdom_name and 
                lineage.get('phylum') == phylum_name and 
                lineage.get('class') is None):
                target_taxon = (taxid, lineage)
                break
    elif len(segments) == 4:
        # Class level
        class_name = segments[3].replace('_', ' ')
        for taxid, lineage in lineage_data.items():
            if (lineage.get('class') == class_name and 
                lineage.get('order') is None):
                target_taxon = (taxid, lineage)
                break
    elif len(segments) == 5:
        # Order level
        order_name = segments[4].replace('_', ' ')
        for taxid, lineage in lineage_data.items():
            if (lineage.get('order') == order_name and 
                lineage.get('family') is None):
                target_taxon = (taxid, lineage)
                break
    elif len(segments) == 6:
        # Family level
        family_name = segments[5].replace('_', ' ')
        for taxid, lineage in lineage_data.items():
            if (lineage.get('family') == family_name and 
                lineage.get('genus') is None):
                target_taxon = (taxid, lineage)
                break
    elif len(segments) == 7:
        # Genus level
        genus_name = segments[6].replace('_', ' ')
        for taxid, lineage in lineage_data.items():
            if (lineage.get('genus') == genus_name and 
                lineage.get('species') is None):
                target_taxon = (taxid, lineage)
                break
    
    if not target_taxon:
        return None
    
    taxid, lineage = target_taxon
    
    # Determine rank and name
    if lineage.get('species'):
        rank = 'species'
        name = lineage['species']
    elif lineage.get('genus'):
        rank = 'genus'
        name = lineage['genus']
    elif lineage.get('family'):
        rank = 'family'
        name = lineage['family']
    elif lineage.get('order'):
        rank = 'order'
        name = lineage['order']
    elif lineage.get('class'):
        rank = 'class'
        name = lineage['class']
    elif lineage.get('phylum'):
        rank = 'phylum'
        name = lineage['phylum']
    else:
        rank = 'kingdom'
        name = lineage['kingdom']
    
    return {
        'id': parent_id,
        'name': name,
        'rank': rank,
        'ncbi_taxid': taxid,
        'ncbi_lineage': {
            'kingdom': lineage.get('kingdom'),
            'phylum': lineage.get('phylum'),
            'class': lineage.get('class'),
            'order': lineage.get('order'),
            'family': lineage.get('family'),
            'genus': lineage.get('genus'),
            'species': lineage.get('species')
        },
        'ncbi_lineage_json': lineage.get('lineage_json')
    }

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
    ncbi_db.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better performance
    ncbi_db.execute("PRAGMA synchronous=NORMAL")  # Reduce sync overhead
    
    try:
        # Pre-load merged taxon mappings for batch processing
        if verbose:
            print("Pre-loading NCBI merged taxon mappings...")
        merged_mappings = {}
        cursor = ncbi_db.cursor()
        cursor.execute("SELECT old_taxid, new_taxid FROM ncbi_merged")
        for old_taxid, new_taxid in cursor.fetchall():
            merged_mappings[old_taxid] = new_taxid
        
        if verbose:
            print(f"Loaded {len(merged_mappings)} merged taxon mappings")
        
        # Pre-load scientific name mappings for batch processing
        if verbose:
            print("Pre-loading NCBI scientific name mappings...")
        scientific_name_mappings = {}
        cursor.execute("""
            SELECT name_txt, taxid 
            FROM ncbi_names 
            WHERE name_class = 'scientific name'
        """)
        for name_txt, taxid in cursor.fetchall():
            scientific_name_mappings[name_txt] = taxid
        
        if verbose:
            print(f"Loaded {len(scientific_name_mappings)} scientific name mappings")
        
        # Verify each taxon with optimized lookups
        verified_taxa = []
        taxa_with_ncbi = 0
        taxa_found = 0
        
        for i, taxon in enumerate(taxa):
            if verbose and i % 50 == 0:
                print(f"Processing taxon {i+1}/{len(taxa)}: {taxon.get('id', 'unknown')}")
            
            verified = verify_ncbi_taxid_optimized(taxon, merged_mappings, scientific_name_mappings)
            verified_taxa.append(verified)
            
            if verified.get('ncbi_taxid'):
                taxa_with_ncbi += 1
                if 'found' in verified.get('_debug', ''):
                    taxa_found += 1
        
        if verbose:
            print(f"NCBI verification complete: {taxa_with_ncbi}/{len(taxa)} taxa have NCBI taxon IDs")
            print(f"Found {taxa_found} new NCBI taxon IDs via scientific name lookup")
        
        # Pre-load NCBI parent relationships for efficient hierarchy walking
        if verbose:
            print("Pre-loading NCBI parent relationships...")
        
        # Get all unique NCBI taxon IDs from verified taxa
        ncbi_taxids = [t.get('ncbi_taxid') for t in verified_taxa if t.get('ncbi_taxid')]
        
        # Load parent relationships from ncbi_nodes table
        parent_relationships = {}
        if ncbi_taxids:
            placeholders = ','.join(['?' for _ in ncbi_taxids])
            cursor.execute(f"""
                SELECT n.taxid, n.parent_taxid, n.rank, names.name_txt
                FROM ncbi_nodes n
                JOIN ncbi_names names ON n.taxid = names.taxid
                WHERE n.taxid IN ({placeholders}) AND names.name_class = 'scientific name'
            """, ncbi_taxids)
            
            for row in cursor.fetchall():
                parent_relationships[row[0]] = {
                    'parent_taxid': row[1],
                    'rank': row[2],
                    'name': row[3]
                }
        
        if verbose:
            print(f"Loaded {len(parent_relationships)} parent relationships for {len(ncbi_taxids)} taxa with NCBI IDs")
        
        # Complete the taxonomic tree
        if verbose:
            print("Completing taxonomic tree...")
        complete_taxa = complete_taxonomic_tree_with_ncbi_hierarchy(verified_taxa, parent_relationships, ncbi_db, verbose)
        
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
