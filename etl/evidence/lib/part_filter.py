#!/usr/bin/env python3
"""
Part Filter for Evidence Mapping

Provides lineage-based part applicability filtering for the 3-tier evidence mapping system.
Uses NCBI lineage data to determine which parts are applicable to specific taxa.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass

# Try absolute imports first, fall back to relative
try:
    from etl.evidence.db import Part
except ImportError:
    # Fall back to relative imports when running from etl directory
    from evidence.db import Part

@dataclass
class PartApplicability:
    """Result of part applicability filtering"""
    part_id: str
    applicable: bool
    confidence: float
    reason: str
    lineage_matches: List[str]

class PartFilter:
    """Lineage-based part applicability filter"""
    
    def __init__(self, graph_db_path: Path):
        """Initialize with path to graph database"""
        self.graph_db_path = graph_db_path
        if not graph_db_path.exists():
            raise FileNotFoundError(f"Graph database not found: {graph_db_path}")
    
    def filter_parts_for_taxon(self, taxon_id: str, lineage: Dict[str, str], 
                             available_parts: List[Dict[str, Any]]) -> List[PartApplicability]:
        """
        Filter parts based on taxon lineage and applicability rules
        
        Args:
            taxon_id: Taxon ID to filter parts for
            lineage: NCBI lineage data for the taxon
            available_parts: List of available parts from ontology
            
        Returns:
            List of PartApplicability results
        """
        results = []
        
        for part in available_parts:
            applicability = self._check_part_applicability(part, taxon_id, lineage)
            results.append(applicability)
        
        return results
    
    def _check_part_applicability(self, part: Part, taxon_id: str, 
                                lineage: Dict[str, str]) -> PartApplicability:
        """Check if a specific part is applicable to a taxon"""
        part_id = part.id
        applies_to = getattr(part, 'applies_to', [])
        kind = getattr(part, 'kind', '')
        
        # If part has explicit applies_to list, check if taxon is included
        if applies_to:
            if taxon_id in applies_to:
                return PartApplicability(
                    part_id=part_id,
                    applicable=True,
                    confidence=1.0,
                    reason="Explicitly listed in applies_to",
                    lineage_matches=[taxon_id]
                )
            else:
                # Check if any parent taxon is in applies_to
                parent_matches = self._check_parent_applicability(taxon_id, applies_to)
                if parent_matches:
                    return PartApplicability(
                        part_id=part_id,
                        applicable=True,
                        confidence=0.8,
                        reason="Parent taxon in applies_to",
                        lineage_matches=parent_matches
                    )
                else:
                    return PartApplicability(
                        part_id=part_id,
                        applicable=False,
                        confidence=0.0,
                        reason="Not in applies_to list",
                        lineage_matches=[]
                    )
        
        # Use lineage-based rules for biological parts
        if kind in ['plant', 'animal', 'fungus']:
            return self._check_lineage_based_applicability(part, taxon_id, lineage)
        
        # For derived parts, check if they can be derived from this taxon
        if kind == 'derived':
            return self._check_derived_part_applicability(part, taxon_id, lineage)
        
        # Default: applicable with low confidence
        return PartApplicability(
            part_id=part_id,
            applicable=True,
            confidence=0.3,
            reason="No specific rules, default applicable",
            lineage_matches=[]
        )
    
    def _check_parent_applicability(self, taxon_id: str, applies_to: List[str]) -> List[str]:
        """Check if any parent taxon is in the applies_to list"""
        matches = []
        segments = taxon_id.split(':')
        
        # Check progressively shorter taxon IDs (parent, grandparent, etc.)
        for i in range(len(segments) - 1, 1, -1):  # Don't go below kingdom level
            parent_id = ':'.join(segments[:i])
            if parent_id in applies_to:
                matches.append(parent_id)
        
        return matches
    
    def _check_lineage_based_applicability(self, part: Part, taxon_id: str, 
                                         lineage: Dict[str, str]) -> PartApplicability:
        """Check applicability based on biological lineage rules"""
        part_id = part.id
        kind = part.kind or ''
        
        # Extract kingdom from lineage or taxon_id
        kingdom = lineage.get('kingdom', '').lower()
        if not kingdom and taxon_id and taxon_id.startswith('tx:'):
            kingdom_code = taxon_id.split(':')[1] if len(taxon_id.split(':')) > 1 else ''
            kingdom_map = {'p': 'plantae', 'a': 'animalia', 'f': 'fungi'}
            kingdom = kingdom_map.get(kingdom_code, '').lower()
        
        # Map NCBI kingdom names to our expected names
        kingdom_mapping = {
            'viridiplantae': 'plantae',
            'metazoa': 'animalia',
            'fungi': 'fungi'
        }
        kingdom = kingdom_mapping.get(kingdom, kingdom)
        
        # Basic kingdom-level filtering
        if kind == 'plant' and kingdom != 'plantae':
            return PartApplicability(
                part_id=part_id,
                applicable=False,
                confidence=0.0,
                reason="Plant part for non-plant taxon",
                lineage_matches=[]
            )
        
        if kind == 'animal' and kingdom != 'animalia':
            return PartApplicability(
                part_id=part_id,
                applicable=False,
                confidence=0.0,
                reason="Animal part for non-animal taxon",
                lineage_matches=[]
            )
        
        if kind == 'fungus' and kingdom != 'fungi':
            return PartApplicability(
                part_id=part_id,
                applicable=False,
                confidence=0.0,
                reason="Fungus part for non-fungus taxon",
                lineage_matches=[]
            )
        
        # Apply specific biological rules based on part type
        part_name = (part.name or '').lower()
        
        # Fruit parts - only for angiosperms
        if 'fruit' in part_name:
            if kingdom == 'plantae':
                # Check if it's an angiosperm (has flowers/fruits)
                class_name = lineage.get('class', '').lower()
                if any(angiosperm_class in class_name for angiosperm_class in ['eudicot', 'monocot', 'magnoliopsida', 'liliopsida']):
                    return PartApplicability(
                        part_id=part_id,
                        applicable=True,
                        confidence=0.9,
                        reason="Fruit part for angiosperm",
                        lineage_matches=[taxon_id]
                    )
                else:
                    return PartApplicability(
                        part_id=part_id,
                        applicable=False,
                        confidence=0.0,
                        reason="Fruit part for non-angiosperm",
                        lineage_matches=[]
                    )
            else:
                return PartApplicability(
                    part_id=part_id,
                    applicable=False,
                    confidence=0.0,
                    reason="Fruit part for non-plant",
                    lineage_matches=[]
                )
        
        # Seed parts - only for seed plants
        if 'seed' in part_name:
            if kingdom == 'plantae':
                # Check if it's a seed plant (not mosses, ferns, etc.)
                class_name = lineage.get('class', '').lower()
                phylum = lineage.get('phylum', '').lower()
                if any(seed_plant in class_name for seed_plant in ['magnoliopsida', 'liliopsida', 'pinopsida', 'gnetopsida']) or \
                   any(seed_plant in phylum for seed_plant in ['streptophyta', 'spermatophyta']):
                    return PartApplicability(
                        part_id=part_id,
                        applicable=True,
                        confidence=0.9,
                        reason="Seed part for seed plant",
                        lineage_matches=[taxon_id]
                    )
                else:
                    return PartApplicability(
                        part_id=part_id,
                        applicable=False,
                        confidence=0.0,
                        reason="Seed part for non-seed plant",
                        lineage_matches=[]
                    )
            else:
                return PartApplicability(
                    part_id=part_id,
                    applicable=False,
                    confidence=0.0,
                    reason="Seed part for non-plant",
                    lineage_matches=[]
                )
        
        # Milk parts - only for mammals
        if 'milk' in part_name:
            if kingdom == 'animalia':
                class_name = lineage.get('class', '').lower()
                if 'mammalia' in class_name or 'mammal' in class_name:
                    return PartApplicability(
                        part_id=part_id,
                        applicable=True,
                        confidence=0.9,
                        reason="Milk part for mammal",
                        lineage_matches=[taxon_id]
                    )
                else:
                    return PartApplicability(
                        part_id=part_id,
                        applicable=False,
                        confidence=0.0,
                        reason="Milk part for non-mammal",
                        lineage_matches=[]
                    )
            else:
                return PartApplicability(
                    part_id=part_id,
                    applicable=False,
                    confidence=0.0,
                    reason="Milk part for non-animal",
                    lineage_matches=[]
                )
        
        # Default: applicable with medium confidence
        return PartApplicability(
            part_id=part_id,
            applicable=True,
            confidence=0.7,
            reason="Lineage-based rules satisfied",
            lineage_matches=[taxon_id]
        )
    
    def _check_derived_part_applicability(self, part: Part, taxon_id: str, 
                                        lineage: Dict[str, str]) -> PartApplicability:
        """Check if a derived part can be derived from this taxon"""
        part_id = part.id
        part_name = (part.name or '').lower()
        
        # Extract kingdom from lineage or taxon_id
        kingdom = lineage.get('kingdom', '').lower()
        if not kingdom and taxon_id and taxon_id.startswith('tx:'):
            kingdom_code = taxon_id.split(':')[1] if len(taxon_id.split(':')) > 1 else ''
            kingdom_map = {'p': 'plantae', 'a': 'animalia', 'f': 'fungi'}
            kingdom = kingdom_map.get(kingdom_code, '').lower()
        
        # Map NCBI kingdom names to our expected names
        kingdom_mapping = {
            'viridiplantae': 'plantae',
            'metazoa': 'animalia',
            'fungi': 'fungi'
        }
        kingdom = kingdom_mapping.get(kingdom, kingdom)
        
        # Oil parts - can be derived from plants and some animals
        if 'oil' in part_name:
            if kingdom in ['plantae', 'animalia']:
                return PartApplicability(
                    part_id=part_id,
                    applicable=True,
                    confidence=0.8,
                    reason="Oil can be derived from plant or animal",
                    lineage_matches=[taxon_id]
                )
            else:
                return PartApplicability(
                    part_id=part_id,
                    applicable=False,
                    confidence=0.0,
                    reason="Oil cannot be derived from this kingdom",
                    lineage_matches=[]
                )
        
        # Flour parts - can be derived from plants
        if 'flour' in part_name or 'meal' in part_name:
            if kingdom == 'plantae':
                return PartApplicability(
                    part_id=part_id,
                    applicable=True,
                    confidence=0.9,
                    reason="Flour can be derived from plant",
                    lineage_matches=[taxon_id]
                )
            else:
                return PartApplicability(
                    part_id=part_id,
                    applicable=False,
                    confidence=0.0,
                    reason="Flour cannot be derived from non-plant",
                    lineage_matches=[]
                )
        
        # Default for derived parts
        return PartApplicability(
            part_id=part_id,
            applicable=True,
            confidence=0.5,
            reason="Derived part generally applicable",
            lineage_matches=[taxon_id]
        )
    
    def get_applicable_parts(self, taxon_id: str, lineage: Dict[str, str], 
                           available_parts: List[Dict[str, Any]], 
                           min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """Get list of applicable parts above confidence threshold"""
        print(f"[PART FILTER] → Checking {len(available_parts)} parts for taxon {taxon_id}")
        print(f"[PART FILTER] → Lineage: {lineage}")
        
        applicability_results = self.filter_parts_for_taxon(taxon_id, lineage, available_parts)
        
        applicable_parts = []
        skipped_count = 0
        for part, applicability in zip(available_parts, applicability_results):
            if applicability.applicable and applicability.confidence >= min_confidence:
                applicable_parts.append(part)
            else:
                skipped_count += 1
        
        print(f"[PART FILTER] → Found {len(applicable_parts)} applicable parts ({skipped_count} skipped)")
        return applicable_parts
