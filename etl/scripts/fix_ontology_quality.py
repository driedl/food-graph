#!/usr/bin/env python3
"""
Ontology Quality Fixer

Fixes data quality issues in our ontology by:
1. Adding NCBI taxon IDs for taxa that have synonym opportunities
2. Flagging orphaned taxa for manual review
3. Updating ontology files with corrected data

This helps clean up our ontology during early development.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import shutil

def load_quality_report(report_path: Path) -> Dict[str, Any]:
    """Load the ontology quality analysis report."""
    with open(report_path, 'r') as f:
        return json.load(f)

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

def find_best_ncbi_match(taxon_name: str, ncbi_db: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    """Find the best NCBI match for a taxon name."""
    cursor = ncbi_db.cursor()
    
    # Search for exact matches, prioritizing scientific names
    cursor.execute("""
        SELECT n.taxid, n.name_class, n.name_txt, nodes.rank
        FROM ncbi_names n
        JOIN ncbi_nodes nodes ON n.taxid = nodes.taxid
        WHERE n.name_txt = ? AND n.name_class IN ('scientific name', 'synonym', 'common name')
        ORDER BY 
            CASE n.name_class 
                WHEN 'scientific name' THEN 1
                WHEN 'synonym' THEN 2
                WHEN 'common name' THEN 3
                ELSE 4
            END
        LIMIT 1
    """, (taxon_name,))
    
    row = cursor.fetchone()
    if row:
        return {
            'taxid': row[0],
            'name_class': row[1],
            'name': row[2],
            'rank': row[3]
        }
    
    return None

def update_taxa_with_ncbi_ids(taxa: List[Dict[str, Any]], synonym_opportunities: List[Dict[str, Any]], ncbi_db: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Update taxa with NCBI taxon IDs from synonym opportunities."""
    updated_taxa = []
    updated_count = 0
    
    # Create a mapping of taxon IDs to synonym opportunities
    synonym_map = {item['taxon_id']: item for item in synonym_opportunities}
    
    for taxon in taxa:
        taxon_id = taxon['id']
        
        if taxon_id in synonym_map:
            # Find the best NCBI match
            best_match = find_best_ncbi_match(taxon['latin_name'], ncbi_db)
            
            if best_match:
                # Update the taxon with NCBI data
                updated_taxon = taxon.copy()
                updated_taxon['ncbi_taxid'] = best_match['taxid']
                updated_taxon['_ncbi_source'] = best_match['name_class']
                updated_taxon['_ncbi_rank'] = best_match['rank']
                updated_taxa.append(updated_taxon)
                updated_count += 1
                
                print(f"✅ Updated {taxon_id}: {taxon['latin_name']} → NCBI taxid {best_match['taxid']} ({best_match['name_class']})")
            else:
                updated_taxa.append(taxon)
                print(f"⚠️  No NCBI match found for {taxon_id}: {taxon['latin_name']}")
        else:
            updated_taxa.append(taxon)
    
    print(f"\n📊 Updated {updated_count} taxa with NCBI taxon IDs")
    return updated_taxa

def flag_orphaned_taxa(orphaned_taxa: List[Dict[str, Any]]) -> None:
    """Flag orphaned taxa for manual review."""
    print(f"\n🚨 ORPHANED TAXA REQUIRING MANUAL REVIEW ({len(orphaned_taxa)}):")
    print("="*60)
    
    for item in orphaned_taxa:
        print(f"\n❌ {item['taxon_id']}: {item['latin_name']}")
        print(f"   Rank: {item['rank']}")
        print(f"   Parent: {item['parent_id']}")
        print(f"   Action needed: Review and either:")
        print(f"     - Find correct NCBI match")
        print(f"     - Remove if invalid")
        print(f"     - Keep if it's a valid non-NCBI taxon")

def create_ontology_fixes_report(orphaned_taxa: List[Dict[str, Any]], synonym_opportunities: List[Dict[str, Any]], output_path: Path) -> None:
    """Create a detailed report of ontology fixes needed."""
    report = {
        'orphaned_taxa': orphaned_taxa,
        'synonym_opportunities': synonym_opportunities,
        'summary': {
            'orphaned_count': len(orphaned_taxa),
            'synonym_opportunities_count': len(synonym_opportunities),
            'total_issues': len(orphaned_taxa) + len(synonym_opportunities)
        },
        'recommendations': [
            "Review orphaned taxa for validity",
            "Add NCBI taxon IDs for synonym opportunities",
            "Consider removing invalid taxa",
            "Update ontology files with corrected data"
        ]
    }
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed fixes report saved to: {output_path}")

def backup_ontology_files(ontology_root: Path, backup_dir: Path) -> None:
    """Create backup of original ontology files."""
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    
    shutil.copytree(ontology_root, backup_dir)
    print(f"📁 Backed up ontology files to: {backup_dir}")

def update_ontology_files_with_ncbi_ids(compiled_taxa: List[Dict[str, Any]], ontology_root: Path, verbose: bool = False) -> None:
    """Update original ontology files with NCBI taxon IDs."""
    # Create mapping of taxon ID to NCBI taxon ID
    ncbi_id_map = {t['id']: t.get('ncbi_taxid') for t in compiled_taxa if t.get('ncbi_taxid')}
    
    if verbose:
        print(f"Updating ontology files with {len(ncbi_id_map)} NCBI taxon IDs...")
    
    updated_count = 0
    
    # Find all JSONL files in ontology
    for jsonl_file in ontology_root.rglob('*.jsonl'):
        if verbose:
            print(f"Updating {jsonl_file.relative_to(ontology_root)}...")
        
        # Read original file
        original_taxa = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                original_taxa.append(json.loads(line))
        
        # Update with NCBI taxon IDs
        file_updated = False
        for taxon in original_taxa:
            taxon_id = taxon.get('id')
            if taxon_id and taxon_id in ncbi_id_map:
                new_ncbi_id = ncbi_id_map[taxon_id]
                if taxon.get('ncbi_taxid') != new_ncbi_id:
                    taxon['ncbi_taxid'] = new_ncbi_id
                    file_updated = True
                    updated_count += 1
                    if verbose:
                        print(f"  Updated {taxon_id} with NCBI taxon ID {new_ncbi_id}")
        
        # Write updated file
        if file_updated:
            with open(jsonl_file, 'w', encoding='utf-8') as f:
                for taxon in original_taxa:
                    f.write(json.dumps(taxon, ensure_ascii=False) + '\n')
    
    print(f"📝 Updated {updated_count} taxa across ontology files")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix ontology data quality issues")
    parser.add_argument("--quality-report", type=Path, required=True,
                        help="Path to ontology quality analysis report JSON")
    parser.add_argument("--compiled-taxa", type=Path, required=True,
                        help="Path to compiled taxa.jsonl from Stage 1")
    parser.add_argument("--ncbi-db", type=Path, required=True,
                        help="Path to NCBI SQLite database")
    parser.add_argument("--ontology-root", type=Path, required=True,
                        help="Path to root directory of ontology files")
    parser.add_argument("--backup-dir", type=Path,
                        help="Directory to backup original ontology files")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be changed without making changes")
    
    args = parser.parse_args()
    
    # Load quality report
    quality_report = load_quality_report(args.quality_report)
    
    print("🔍 ONTOLOGY QUALITY FIXER")
    print("="*50)
    
    # Show summary
    summary = quality_report['summary']
    print(f"\n📊 ISSUES FOUND:")
    print(f"  Orphaned taxa: {summary['orphaned_count']}")
    print(f"  Synonym opportunities: {summary['synonym_opportunities_count']}")
    print(f"  Total issues: {summary['orphaned_count'] + summary['synonym_opportunities_count']}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
    
    # Load data
    compiled_taxa = load_compiled_taxa(args.compiled_taxa)
    ncbi_db = load_ncbi_db(args.ncbi_db)
    
    try:
        # 1. Flag orphaned taxa for manual review
        flag_orphaned_taxa(quality_report['orphaned_taxa'])
        
        # 2. Update taxa with NCBI IDs from synonym opportunities
        if not args.dry_run:
            updated_taxa = update_taxa_with_ncbi_ids(
                compiled_taxa, 
                quality_report['synonym_opportunities'], 
                ncbi_db
            )
            
            # 3. Update ontology files with NCBI taxon IDs
            if args.ontology_root.exists():
                # Create backup if requested
                if args.backup_dir:
                    backup_ontology_files(args.ontology_root, args.backup_dir)
                
                # Update ontology files
                update_ontology_files_with_ncbi_ids(updated_taxa, args.ontology_root, args.verbose)
            else:
                print(f"⚠️  Ontology root directory not found: {args.ontology_root}")
        
        # 4. Create fixes report
        fixes_report_path = args.quality_report.parent / "ontology_fixes_report.json"
        create_ontology_fixes_report(
            quality_report['orphaned_taxa'],
            quality_report['synonym_opportunities'],
            fixes_report_path
        )
        
        print(f"\n✅ ONTOLOGY QUALITY FIXES COMPLETE!")
        print(f"   - Orphaned taxa flagged for manual review")
        print(f"   - Synonym opportunities processed")
        print(f"   - Ontology files updated with NCBI taxon IDs")
        print(f"   - Detailed report saved")
        
    finally:
        ncbi_db.close()

if __name__ == "__main__":
    main()
