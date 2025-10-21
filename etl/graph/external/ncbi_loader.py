#!/usr/bin/env python3
"""
NCBI Taxonomy Loader

Downloads and parses NCBI taxonomy data (taxdump) and builds a SQLite index
with FTS5 for fast scientific name lookups.

Usage:
    python ncbi_loader.py --output etl/build/database/ncbi.sqlite
"""

from __future__ import annotations
import argparse
import sqlite3
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import urllib.request
import json

NCBI_TAXDUMP_URL = "ftp://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz"

def download_taxdump(output_dir: Path) -> Path:
    """Download NCBI taxdump to temporary directory."""
    print("Downloading NCBI taxdump...")
    tar_path = output_dir / "taxdump.tar.gz"
    
    urllib.request.urlretrieve(NCBI_TAXDUMP_URL, tar_path)
    print(f"Downloaded to {tar_path}")
    return tar_path

def parse_names_file(names_path: Path) -> List[Tuple[int, str, str]]:
    """Parse names.dmp file into (taxid, name_txt, name_class) tuples."""
    print("Parsing names.dmp...")
    names = []
    
    with open(names_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Format: taxid | name_txt | unique name | name class |
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                taxid = int(parts[0])
                name_txt = parts[1]
                name_class = parts[3]
                names.append((taxid, name_txt, name_class))
    
    print(f"Parsed {len(names)} names")
    return names

def parse_nodes_file(nodes_path: Path) -> List[Tuple[int, int, str, int]]:
    """Parse nodes.dmp file into (taxid, parent_taxid, rank, division_id) tuples."""
    print("Parsing nodes.dmp...")
    nodes = []
    
    with open(nodes_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Format: taxid | parent taxid | rank | embl code | division id | ... |
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 6:
                taxid = int(parts[0])
                parent_taxid = int(parts[1]) if parts[1] != '1' else None
                rank = parts[2]
                division_id = int(parts[4])
                nodes.append((taxid, parent_taxid, rank, division_id))
    
    print(f"Parsed {len(nodes)} nodes")
    return nodes

def parse_merged_file(merged_path: Path) -> List[Tuple[int, int]]:
    """Parse merged.dmp file into (old_taxid, new_taxid) tuples."""
    print("Parsing merged.dmp...")
    merged = []
    
    with open(merged_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Format: old_taxid | new_taxid |
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 2:
                old_taxid = int(parts[0])
                new_taxid = int(parts[1])
                merged.append((old_taxid, new_taxid))
    
    print(f"Parsed {len(merged)} merged entries")
    return merged

def compute_lineage(nodes: List[Tuple[int, int, str, int]]) -> Dict[int, Dict[str, str]]:
    """Compute lineage for each taxid."""
    print("Computing lineages...")
    
    # Build parent lookup
    parent_map = {taxid: parent for taxid, parent, _, _ in nodes if parent is not None}
    
    # Build rank lookup
    rank_map = {taxid: rank for taxid, _, rank, _ in nodes}
    
    # Compute lineage for each node
    lineages = {}
    
    def get_lineage(taxid: int) -> Dict[str, str]:
        if taxid in lineages:
            return lineages[taxid]
        
        lineage = {}
        current = taxid
        
        # Walk up the tree
        while current in parent_map:
            rank = rank_map.get(current, '')
            if rank in ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']:
                lineage[rank] = str(current)  # Store taxid for now, will resolve to names later
            current = parent_map[current]
        
        lineages[taxid] = lineage
        return lineage
    
    # Compute for all nodes
    for taxid, _, _, _ in nodes:
        get_lineage(taxid)
    
    print(f"Computed lineages for {len(lineages)} nodes")
    return lineages

def build_sqlite_index(
    names: List[Tuple[int, str, str]],
    nodes: List[Tuple[int, int, str, int]],
    merged: List[Tuple[int, int]],
    lineages: Dict[int, Dict[str, str]],
    output_path: Path
) -> None:
    """Build SQLite database with FTS5 index."""
    print(f"Building SQLite index at {output_path}")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing database
    if output_path.exists():
        output_path.unlink()
    
    conn = sqlite3.connect(str(output_path))
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE ncbi_names (
            taxid INTEGER NOT NULL,
            name_txt TEXT NOT NULL,
            name_class TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE ncbi_nodes (
            taxid INTEGER PRIMARY KEY,
            parent_taxid INTEGER,
            rank TEXT NOT NULL,
            division_id INTEGER NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE ncbi_merged (
            old_taxid INTEGER PRIMARY KEY,
            new_taxid INTEGER NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE ncbi_lineage (
            taxid INTEGER PRIMARY KEY,
            kingdom TEXT,
            phylum TEXT,
            class TEXT,
            order_name TEXT,
            family TEXT,
            genus TEXT,
            species TEXT,
            lineage_json TEXT
        )
    """)
    
    # Create FTS5 virtual table for names
    cursor.execute("""
        CREATE VIRTUAL TABLE ncbi_names_fts USING fts5(
            taxid,
            name_txt,
            name_class,
            content='ncbi_names',
            content_rowid='rowid'
        )
    """)
    
    # Insert data
    print("Inserting names...")
    cursor.executemany(
        "INSERT INTO ncbi_names (taxid, name_txt, name_class) VALUES (?, ?, ?)",
        names
    )
    
    print("Inserting nodes...")
    cursor.executemany(
        "INSERT INTO ncbi_nodes (taxid, parent_taxid, rank, division_id) VALUES (?, ?, ?, ?)",
        nodes
    )
    
    print("Inserting merged...")
    cursor.executemany(
        "INSERT INTO ncbi_merged (old_taxid, new_taxid) VALUES (?, ?)",
        merged
    )
    
    print("Inserting lineages...")
    for taxid, lineage in lineages.items():
        lineage_json = json.dumps(lineage)
        cursor.execute("""
            INSERT INTO ncbi_lineage (taxid, kingdom, phylum, class, order_name, family, genus, species, lineage_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            taxid,
            lineage.get('kingdom'),
            lineage.get('phylum'),
            lineage.get('class'),
            lineage.get('order'),
            lineage.get('family'),
            lineage.get('genus'),
            lineage.get('species'),
            lineage_json
        ))
    
    # Populate FTS5 index
    print("Populating FTS5 index...")
    cursor.execute("INSERT INTO ncbi_names_fts(ncbi_names_fts) VALUES('rebuild')")
    
    # Create indexes
    print("Creating indexes...")
    cursor.execute("CREATE INDEX idx_ncbi_names_taxid ON ncbi_names(taxid)")
    cursor.execute("CREATE INDEX idx_ncbi_names_class ON ncbi_names(name_class)")
    cursor.execute("CREATE INDEX idx_ncbi_nodes_parent ON ncbi_nodes(parent_taxid)")
    cursor.execute("CREATE INDEX idx_ncbi_nodes_rank ON ncbi_nodes(rank)")
    
    conn.commit()
    conn.close()
    
    print(f"NCBI database built successfully at {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Build NCBI taxonomy SQLite index")
    parser.add_argument("--output", required=True, type=Path, help="Output SQLite database path")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary files")
    
    args = parser.parse_args()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Download taxdump
        tar_path = download_taxdump(temp_path)
        
        # Extract files
        print("Extracting taxdump...")
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(temp_path)
        
        # Parse files
        names = parse_names_file(temp_path / "names.dmp")
        nodes = parse_nodes_file(temp_path / "nodes.dmp")
        merged = parse_merged_file(temp_path / "merged.dmp")
        
        # Compute lineages
        lineages = compute_lineage(nodes)
        
        # Build SQLite index
        build_sqlite_index(names, nodes, merged, lineages, args.output)
        
        if args.keep_temp:
            print(f"Temporary files kept in {temp_path}")
        else:
            print("Temporary files cleaned up")

if __name__ == "__main__":
    main()
