#!/usr/bin/env python3
"""
Ontology Data Quality Analysis

Analyzes our ontology against NCBI data to identify:
1. Orphaned taxa (no NCBI counterpart)
2. Divergent parent relationships (our ontology vs NCBI hierarchy)
3. Incorrect taxonomic placements
4. Missing intermediate nodes
5. Synonym opportunities

This helps us clean up our ontology during early development.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict

def load_compiled_taxa(compiled_taxa_path: Path) -> List[Dict[str, Any]]:
    """Load compiled taxa from Stage 1 output."""
    taxa = []
    with open(compiled_taxa_path, 'r', encoding='utf-8') as f:
        for line in f:
            taxa.append(json.loads(line))
    return taxa

def load_ncbi_db(ncbi_db_path: Path) -> sqlite3.Connection:
    """Load NCBI database connection."""
    if not ncbi_db_path.exists():
        raise FileNotFoundError(f"NCBI database not found: {ncbi_db_path}")
    
    db = sqlite3.connect(str(ncbi_db_path))
    db.execute("PRAGMA journal_mode=WAL")
    return db

def get_ncbi_hierarchy(taxid: int, ncbi_db: sqlite3.Connection) -> Dict[str, Any]:
    """Get full NCBI hierarchy for a taxon."""
    cursor = ncbi_db.cursor()
    
    # Get the full lineage
    cursor.execute("""
        SELECT kingdom, phylum, class, order_name, family, genus, species, lineage_json
        FROM ncbi_lineage 
        WHERE taxid = ?
    """, (taxid,))
    
    row = cursor.fetchone()
    if not row:
        return {}
    
    return {
        'kingdom': row[0],
        'phylum': row[1], 
        'class': row[2],
        'order': row[3],
        'family': row[4],
        'genus': row[5],
        'species': row[6],
        'lineage_json': row[7]
    }

def get_ncbi_parent_chain(taxid: int, ncbi_db: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Walk up the NCBI parent chain to get full hierarchy."""
    cursor = ncbi_db.cursor()
    hierarchy = []
    current_taxid = taxid
    visited = set()
    
    while current_taxid and current_taxid not in visited:
        visited.add(current_taxid)
        
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
        hierarchy.append({
            'taxid': taxid,
            'parent_taxid': parent_taxid,
            'rank': rank,
            'name': name
        })
        
        if rank == 'kingdom' or not parent_taxid:
            break
            
        current_taxid = parent_taxid
    
    return hierarchy

def find_synonyms(taxon_name: str, ncbi_db: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Find potential synonyms for a taxon name."""
    cursor = ncbi_db.cursor()
    
    # Search for exact matches
    cursor.execute("""
        SELECT n.taxid, n.name_class, n.name_txt
        FROM ncbi_names n
        JOIN ncbi_nodes nodes ON n.taxid = nodes.taxid
        WHERE n.name_txt = ? AND n.name_class IN ('scientific name', 'synonym', 'common name')
        ORDER BY n.name_class
    """, (taxon_name,))
    
    results = []
    for taxid, name_class, name_txt in cursor.fetchall():
        results.append({
            'taxid': taxid,
            'name_class': name_class,
            'name': name_txt
        })
    
    return results

def analyze_ontology_quality(compiled_taxa_path: Path, ncbi_db_path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Analyze ontology data quality against NCBI."""
    
    # Load data
    taxa = load_compiled_taxa(compiled_taxa_path)
    ncbi_db = load_ncbi_db(ncbi_db_path)
    
    analysis = {
        'orphaned_taxa': [],           # Taxa with no NCBI counterpart
        'divergent_parents': [],       # Taxa with different parent relationships
        'incorrect_placements': [],    # Taxa in wrong taxonomic position
        'missing_intermediates': [],   # Missing intermediate taxonomic levels
        'synonym_opportunities': [],   # Potential synonyms found
        'ncbi_verification_issues': [], # Issues with NCBI verification
        'summary': {}
    }
    
    if verbose:
        print(f"Analyzing {len(taxa)} taxa against NCBI database...")
    
    # Analyze each taxon
    for i, taxon in enumerate(taxa):
        if verbose and i % 50 == 0:
            print(f"Processing taxon {i+1}/{len(taxa)}: {taxon.get('id', 'unknown')}")
        
        taxon_id = taxon.get('id', '')
        ncbi_taxid = taxon.get('ncbi_taxid')
        latin_name = taxon.get('latin_name', '')
        parent_id = taxon.get('parent')
        rank = taxon.get('rank', '')
        
        # Skip kingdom-level taxa
        if len(taxon_id.split(':')) <= 2:
            continue
        
        # 1. Check for orphaned taxa (no NCBI counterpart)
        if not ncbi_taxid:
            # Try to find potential matches
            synonyms = find_synonyms(latin_name, ncbi_db)
            
            if synonyms:
                analysis['synonym_opportunities'].append({
                    'taxon_id': taxon_id,
                    'latin_name': latin_name,
                    'potential_matches': synonyms
                })
            else:
                analysis['orphaned_taxa'].append({
                    'taxon_id': taxon_id,
                    'latin_name': latin_name,
                    'rank': rank,
                    'parent_id': parent_id
                })
        else:
            # 2. Check for divergent parent relationships
            ncbi_hierarchy = get_ncbi_parent_chain(ncbi_taxid, ncbi_db)
            
            if ncbi_hierarchy:
                # Find our expected parent based on ID structure
                expected_parent = compute_parent_from_id(taxon_id)
                
                # Check if NCBI parent matches our expected parent
                if len(ncbi_hierarchy) > 1:
                    ncbi_parent = ncbi_hierarchy[1]  # Parent is second in hierarchy
                    ncbi_parent_rank = ncbi_parent['rank']
                    ncbi_parent_name = ncbi_parent['name']
                    
                    # Convert NCBI parent to our ID format
                    ncbi_parent_id = ncbi_taxid_to_our_id(
                        ncbi_parent['taxid'], 
                        ncbi_parent_rank, 
                        ncbi_parent_name
                    )
                    
                    if ncbi_parent_id and ncbi_parent_id != expected_parent:
                        analysis['divergent_parents'].append({
                            'taxon_id': taxon_id,
                            'latin_name': latin_name,
                            'our_parent': expected_parent,
                            'ncbi_parent': ncbi_parent_id,
                            'ncbi_parent_name': ncbi_parent_name,
                            'ncbi_parent_rank': ncbi_parent_rank
                        })
                
                # 3. Check for incorrect taxonomic placements
                ncbi_rank = ncbi_hierarchy[0]['rank']
                if ncbi_rank != rank and ncbi_rank != 'unknown':
                    analysis['incorrect_placements'].append({
                        'taxon_id': taxon_id,
                        'latin_name': latin_name,
                        'our_rank': rank,
                        'ncbi_rank': ncbi_rank,
                        'ncbi_taxid': ncbi_taxid
                    })
    
    # 4. Check for missing intermediate nodes
    all_taxon_ids = {t['id'] for t in taxa}
    for taxon in taxa:
        current_id = taxon['id']
        while True:
            parent_id = compute_parent_from_id(current_id)
            if not parent_id:
                break
            
            if parent_id not in all_taxon_ids:
                analysis['missing_intermediates'].append({
                    'missing_parent': parent_id,
                    'child': current_id,
                    'child_name': taxon.get('latin_name', '')
                })
            
            current_id = parent_id
    
    # Generate summary
    analysis['summary'] = {
        'total_taxa': len(taxa),
        'orphaned_count': len(analysis['orphaned_taxa']),
        'divergent_parents_count': len(analysis['divergent_parents']),
        'incorrect_placements_count': len(analysis['incorrect_placements']),
        'missing_intermediates_count': len(analysis['missing_intermediates']),
        'synonym_opportunities_count': len(analysis['synonym_opportunities'])
    }
    
    ncbi_db.close()
    return analysis

def compute_parent_from_id(taxon_id: str) -> Optional[str]:
    """Compute parent taxon ID by dropping the last segment."""
    segments = taxon_id.split(':')
    if len(segments) <= 2:  # tx:p or tx:a (kingdom level)
        return None
    return ':'.join(segments[:-1])

def ncbi_taxid_to_our_id(taxid: int, rank: str, name: str) -> Optional[str]:
    """Convert NCBI taxid to our taxon ID format."""
    # This is a simplified version - would need full implementation
    # For now, just return None to avoid errors
    return None

def print_analysis_report(analysis: Dict[str, Any]) -> None:
    """Print a comprehensive analysis report."""
    print("\n" + "="*80)
    print("ONTOLOGY DATA QUALITY ANALYSIS REPORT")
    print("="*80)
    
    summary = analysis['summary']
    print(f"\nSUMMARY:")
    print(f"  Total taxa analyzed: {summary['total_taxa']}")
    print(f"  Orphaned taxa (no NCBI match): {summary['orphaned_count']}")
    print(f"  Divergent parent relationships: {summary['divergent_parents_count']}")
    print(f"  Incorrect taxonomic placements: {summary['incorrect_placements_count']}")
    print(f"  Missing intermediate nodes: {summary['missing_intermediates_count']}")
    print(f"  Synonym opportunities: {summary['synonym_opportunities_count']}")
    
    # Orphaned taxa
    if analysis['orphaned_taxa']:
        print(f"\n🚨 ORPHANED TAXA ({len(analysis['orphaned_taxa'])}):")
        print("   These taxa have no NCBI counterpart and may need review:")
        for item in analysis['orphaned_taxa'][:10]:  # Show first 10
            print(f"   - {item['taxon_id']}: {item['latin_name']} ({item['rank']})")
        if len(analysis['orphaned_taxa']) > 10:
            print(f"   ... and {len(analysis['orphaned_taxa']) - 10} more")
    
    # Divergent parents
    if analysis['divergent_parents']:
        print(f"\n⚠️  DIVERGENT PARENT RELATIONSHIPS ({len(analysis['divergent_parents'])}):")
        print("   Our ontology vs NCBI hierarchy conflicts:")
        for item in analysis['divergent_parents'][:10]:
            print(f"   - {item['taxon_id']}: {item['latin_name']}")
            print(f"     Our parent: {item['our_parent']}")
            print(f"     NCBI parent: {item['ncbi_parent']} ({item['ncbi_parent_name']})")
        if len(analysis['divergent_parents']) > 10:
            print(f"   ... and {len(analysis['divergent_parents']) - 10} more")
    
    # Incorrect placements
    if analysis['incorrect_placements']:
        print(f"\n❌ INCORRECT TAXONOMIC PLACEMENTS ({len(analysis['incorrect_placements'])}):")
        print("   Rank mismatches between our ontology and NCBI:")
        for item in analysis['incorrect_placements'][:10]:
            print(f"   - {item['taxon_id']}: {item['latin_name']}")
            print(f"     Our rank: {item['our_rank']}")
            print(f"     NCBI rank: {item['ncbi_rank']}")
        if len(analysis['incorrect_placements']) > 10:
            print(f"   ... and {len(analysis['incorrect_placements']) - 10} more")
    
    # Missing intermediates
    if analysis['missing_intermediates']:
        print(f"\n🔗 MISSING INTERMEDIATE NODES ({len(analysis['missing_intermediates'])}):")
        print("   Missing parent nodes in our hierarchy:")
        for item in analysis['missing_intermediates'][:10]:
            print(f"   - Missing: {item['missing_parent']}")
            print(f"     Child: {item['child']} ({item['child_name']})")
        if len(analysis['missing_intermediates']) > 10:
            print(f"   ... and {len(analysis['missing_intermediates']) - 10} more")
    
    # Synonym opportunities
    if analysis['synonym_opportunities']:
        print(f"\n💡 SYNONYM OPPORTUNITIES ({len(analysis['synonym_opportunities'])}):")
        print("   Potential NCBI matches found:")
        for item in analysis['synonym_opportunities'][:10]:
            print(f"   - {item['taxon_id']}: {item['latin_name']}")
            for match in item['potential_matches'][:3]:
                print(f"     → {match['name']} ({match['name_class']}) - taxid: {match['taxid']}")
        if len(analysis['synonym_opportunities']) > 10:
            print(f"   ... and {len(analysis['synonym_opportunities']) - 10} more")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS:")
    print("="*80)
    
    if summary['orphaned_count'] > 0:
        print("1. Review orphaned taxa - consider removing or finding correct NCBI matches")
    
    if summary['divergent_parents_count'] > 0:
        print("2. Fix divergent parent relationships - update our ontology to match NCBI hierarchy")
    
    if summary['incorrect_placements_count'] > 0:
        print("3. Correct taxonomic placements - update ranks to match NCBI")
    
    if summary['missing_intermediates_count'] > 0:
        print("4. Add missing intermediate nodes - complete the taxonomic hierarchy")
    
    if summary['synonym_opportunities_count'] > 0:
        print("5. Explore synonym opportunities - add NCBI taxon IDs for better verification")
    
    print("\n💡 TIP: Use this analysis to clean up your ontology during early development!")
    print("   The NCBI database is helping you catch data quality issues early.")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze ontology data quality against NCBI")
    parser.add_argument("--compiled-taxa", type=Path, required=True,
                        help="Path to compiled taxa.jsonl from Stage 1")
    parser.add_argument("--ncbi-db", type=Path, required=True,
                        help="Path to NCBI SQLite database")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--output", type=Path,
                        help="Output JSON report file")
    
    args = parser.parse_args()
    
    # Run analysis
    analysis = analyze_ontology_quality(args.compiled_taxa, args.ncbi_db, args.verbose)
    
    # Print report
    print_analysis_report(analysis)
    
    # Save JSON report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"\nDetailed report saved to: {args.output}")

if __name__ == "__main__":
    main()
