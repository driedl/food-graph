#!/usr/bin/env python3
"""
NCBI Resolver for Evidence Mapping

Provides NCBI-based taxon verification and resolution for the 3-tier evidence mapping system.
Uses the NCBI database built by the ETL pipeline to verify and resolve taxon IDs.
"""

from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class NCBIResolution:
    """Result of NCBI taxon resolution"""
    taxon_id: str
    ncbi_taxid: Optional[int]
    confidence: float
    lineage: Dict[str, str]
    needs_refinement: bool
    reason: str

class NCBIResolver:
    """NCBI-based taxon resolver for evidence mapping"""
    
    def __init__(self, ncbi_db_path: Path):
        """Initialize with path to NCBI SQLite database"""
        self.ncbi_db_path = ncbi_db_path
        if not ncbi_db_path.exists():
            raise FileNotFoundError(f"NCBI database not found: {ncbi_db_path}")
    
    def resolve_taxon(self, taxon_id: str, verbose: bool = False) -> NCBIResolution:
        """
        Resolve a taxon ID using NCBI database
        
        Args:
            taxon_id: Taxon ID in format tx:{k}:{genus}:{species}[:{cultivar/breed}]
            verbose: Enable verbose logging
            
        Returns:
            NCBIResolution with resolution details
        """
        if not taxon_id.startswith('tx:'):
            return NCBIResolution(
                taxon_id=taxon_id,
                ncbi_taxid=None,
                confidence=0.0,
                lineage={},
                needs_refinement=True,
                reason="Invalid taxon ID format"
            )
        
        # Parse taxon ID
        segments = taxon_id.split(':')
        if len(segments) < 3:
            return NCBIResolution(
                taxon_id=taxon_id,
                ncbi_taxid=None,
                confidence=0.0,
                lineage={},
                needs_refinement=True,
                reason="Insufficient taxonomic depth"
            )
        
        kingdom = segments[1]
        genus = segments[2] if len(segments) > 2 else None
        species = segments[3] if len(segments) > 3 else None
        
        with sqlite3.connect(str(self.ncbi_db_path)) as conn:
            # Try to find exact match first
            exact_match = self._find_exact_match(conn, genus, species)
            if exact_match:
                return self._create_resolution(taxon_id, exact_match, confidence=0.9, reason="Exact NCBI match")
            
            # Try fuzzy matching
            fuzzy_match = self._find_fuzzy_match(conn, genus, species, kingdom)
            if fuzzy_match:
                return self._create_resolution(taxon_id, fuzzy_match, confidence=0.7, reason="Fuzzy NCBI match")
            
            # Try genus-level match
            genus_match = self._find_genus_match(conn, genus, kingdom)
            if genus_match:
                return self._create_resolution(taxon_id, genus_match, confidence=0.5, reason="Genus-level NCBI match")
            
            # No match found
            return NCBIResolution(
                taxon_id=taxon_id,
                ncbi_taxid=None,
                confidence=0.0,
                lineage={},
                needs_refinement=True,
                reason="No NCBI match found"
            )
    
    def _find_exact_match(self, conn: sqlite3.Connection, genus: str, species: str) -> Optional[Dict[str, Any]]:
        """Find exact genus+species match in NCBI database"""
        if not genus or not species:
            return None
        
        cursor = conn.cursor()
        # First find the taxon ID for the species name
        cursor.execute("""
            SELECT taxid FROM ncbi_names 
            WHERE name_txt = ? AND name_class = 'scientific name'
        """, (f"{genus} {species}",))
        
        result = cursor.fetchone()
        if not result:
            return None
        
        taxid = result[0]
        
        # Now get the lineage information
        cursor.execute("""
            SELECT taxid, kingdom, phylum, class, order_name, family, genus, species, lineage_json
            FROM ncbi_lineage 
            WHERE taxid = ?
        """, (taxid,))
        
        lineage_result = cursor.fetchone()
        if not lineage_result:
            return None
        
        # Get the actual genus and species names from the names table
        cursor.execute("""
            SELECT name_txt FROM ncbi_names 
            WHERE taxid = ? AND name_class = 'scientific name'
        """, (taxid,))
        
        name_result = cursor.fetchone()
        scientific_name = name_result[0] if name_result else f"{genus} {species}"
        
        return {
            'taxid': lineage_result[0],
            'name': scientific_name,
            'kingdom': lineage_result[1],
            'phylum': lineage_result[2],
            'class': lineage_result[3],
            'order': lineage_result[4],
            'family': lineage_result[5],
            'genus': lineage_result[6],
            'species': lineage_result[7],
            'lineage_json': lineage_result[8]
        }
    
    def _find_fuzzy_match(self, conn: sqlite3.Connection, genus: str, species: str, kingdom: str) -> Optional[Dict[str, Any]]:
        """Find fuzzy match using FTS5 search"""
        if not genus or not species:
            return None
        
        cursor = conn.cursor()
        # Search for genus and species using FTS5
        cursor.execute("""
            SELECT taxid FROM ncbi_names_fts 
            WHERE name_txt MATCH ? AND name_class = 'scientific name'
            ORDER BY taxid
            LIMIT 1
        """, (f'"{genus}" "{species}"',))
        
        result = cursor.fetchone()
        if not result:
            return None
        
        taxid = result[0]
        
        # Get the lineage information
        cursor.execute("""
            SELECT taxid, kingdom, phylum, class, order_name, family, genus, species, lineage_json
            FROM ncbi_lineage 
            WHERE taxid = ?
        """, (taxid,))
        
        lineage_result = cursor.fetchone()
        if not lineage_result:
            return None
        
        # Get the actual genus and species names from the names table
        cursor.execute("""
            SELECT name_txt FROM ncbi_names 
            WHERE taxid = ? AND name_class = 'scientific name'
        """, (taxid,))
        
        name_result = cursor.fetchone()
        scientific_name = name_result[0] if name_result else f"{genus} {species}"
        
        return {
            'taxid': lineage_result[0],
            'name': scientific_name,
            'kingdom': lineage_result[1],
            'phylum': lineage_result[2],
            'class': lineage_result[3],
            'order': lineage_result[4],
            'family': lineage_result[5],
            'genus': lineage_result[6],
            'species': lineage_result[7],
            'lineage_json': lineage_result[8]
        }
    
    def _find_genus_match(self, conn: sqlite3.Connection, genus: str, kingdom: str) -> Optional[Dict[str, Any]]:
        """Find genus-level match"""
        if not genus:
            return None
        
        cursor = conn.cursor()
        # Search for genus using FTS5
        cursor.execute("""
            SELECT taxid FROM ncbi_names_fts 
            WHERE name_txt MATCH ? AND name_class = 'scientific name'
            ORDER BY taxid
            LIMIT 1
        """, (f'"{genus}"',))
        
        result = cursor.fetchone()
        if not result:
            return None
        
        taxid = result[0]
        
        # Get the lineage information
        cursor.execute("""
            SELECT taxid, kingdom, phylum, class, order_name, family, genus, species, lineage_json
            FROM ncbi_lineage 
            WHERE taxid = ?
        """, (taxid,))
        
        lineage_result = cursor.fetchone()
        if not lineage_result:
            return None
        
        # Get the actual genus and species names from the names table
        cursor.execute("""
            SELECT name_txt FROM ncbi_names 
            WHERE taxid = ? AND name_class = 'scientific name'
        """, (taxid,))
        
        name_result = cursor.fetchone()
        scientific_name = name_result[0] if name_result else f"{genus}"
        
        return {
            'taxid': lineage_result[0],
            'name': scientific_name,
            'kingdom': lineage_result[1],
            'phylum': lineage_result[2],
            'class': lineage_result[3],
            'order': lineage_result[4],
            'family': lineage_result[5],
            'genus': lineage_result[6],
            'species': lineage_result[7],
            'lineage_json': lineage_result[8]
        }
    
    def _create_resolution(self, taxon_id: str, match: Dict[str, Any], confidence: float, reason: str) -> NCBIResolution:
        """Create NCBIResolution from database match"""
        lineage = json.loads(match.get('lineage_json', '{}')) if match.get('lineage_json') else {}
        
        # Resolve taxon IDs to actual names
        resolved_lineage = self._resolve_lineage_names(match['taxid'], lineage)
        
        return NCBIResolution(
            taxon_id=taxon_id,
            ncbi_taxid=match['taxid'],
            confidence=confidence,
            lineage=resolved_lineage,
            needs_refinement=confidence < 0.8,
            reason=reason
        )
    
    def _resolve_lineage_names(self, taxid: int, lineage: Dict[str, str]) -> Dict[str, str]:
        """Resolve taxon IDs in lineage to actual names"""
        resolved = {}
        
        with sqlite3.connect(str(self.ncbi_db_path)) as conn:
            cursor = conn.cursor()
            
            for rank, taxon_id in lineage.items():
                if taxon_id and taxon_id.isdigit():
                    cursor.execute("""
                        SELECT name_txt FROM ncbi_names 
                        WHERE taxid = ? AND name_class = 'scientific name'
                    """, (int(taxon_id),))
                    
                    result = cursor.fetchone()
                    if result:
                        resolved[rank] = result[0]
                    else:
                        resolved[rank] = taxon_id  # Fallback to ID if name not found
                else:
                    resolved[rank] = taxon_id
        
        return resolved
    
    def get_lineage_for_taxon(self, taxon_id: str) -> Dict[str, str]:
        """Get full lineage for a taxon ID"""
        resolution = self.resolve_taxon(taxon_id)
        return resolution.lineage
    
    def verify_taxon_exists(self, taxon_id: str) -> bool:
        """Check if taxon ID exists in NCBI database"""
        resolution = self.resolve_taxon(taxon_id)
        return resolution.ncbi_taxid is not None and resolution.confidence > 0.5
