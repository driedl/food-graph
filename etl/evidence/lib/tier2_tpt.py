#!/usr/bin/env python3
"""
Tier-2: TPT Constructor

Second tier of the 3-tier evidence mapping system. Takes resolved taxa from Tier-1
and constructs Taxon-Part-Transform (TPT) combinations using lineage-based part filtering.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from .tier1_taxon import TaxonResolution
from .part_filter import PartFilter, PartApplicability
from .llm import call_llm

# Try absolute imports first, fall back to relative
try:
    from etl.evidence.db import Part, Transform
except ImportError:
    # Fall back to relative imports when running from etl directory
    from evidence.db import Part, Transform

@dataclass
class TPTConstruction:
    """Result of TPT construction"""
    food_id: str
    food_name: str
    taxon_id: str
    part_id: Optional[str]
    transforms: List[Dict[str, Any]]
    confidence: float
    disposition: str  # 'constructed', 'ambiguous', 'skip'
    reason: str
    applicable_parts: List[Dict[str, Any]]
    new_parts: List[Dict[str, Any]]
    new_transforms: List[Dict[str, Any]]

class Tier2TPTConstructor:
    """Tier-2: TPT constructor with lineage-based part filtering"""
    
    def __init__(self, part_filter: PartFilter, model: str = "gpt-5-mini"):
        """Initialize with part filter and LLM model"""
        self.part_filter = part_filter
        self.model = model
    
    def construct_tpt(self, taxon_resolution: TaxonResolution, 
                     available_parts: List[Dict[str, Any]], 
                     available_transforms: List[Dict[str, Any]]) -> TPTConstruction:
        """
        Construct TPT for a resolved taxon
        
        Args:
            taxon_resolution: Taxon resolution from Tier-1
            available_parts: Available parts from ontology
            available_transforms: Available transforms from ontology
            
        Returns:
            TPTConstruction with TPT combination
        """
        if not taxon_resolution.taxon_id or taxon_resolution.disposition != 'resolved':
            return TPTConstruction(
                food_id=taxon_resolution.food_id,
                food_name=taxon_resolution.food_name,
                taxon_id=taxon_resolution.taxon_id or '',
                part_id=None,
                transforms=[],
                confidence=0.0,
                disposition='skip',
                reason="No valid taxon resolution",
                applicable_parts=[],
                new_parts=[],
                new_transforms=[]
            )
        
        # Get lineage for part filtering
        lineage = taxon_resolution.ncbi_resolution.lineage if taxon_resolution.ncbi_resolution else {}
        
        # Filter applicable parts
        applicable_parts = self.part_filter.get_applicable_parts(
            taxon_resolution.taxon_id, 
            lineage, 
            available_parts,
            min_confidence=0.5
        )
        
        if not applicable_parts:
            return TPTConstruction(
                food_id=taxon_resolution.food_id,
                food_name=taxon_resolution.food_name,
                taxon_id=taxon_resolution.taxon_id,
                part_id=None,
                transforms=[],
                confidence=0.0,
                disposition='skip',
                reason="No applicable parts found",
                applicable_parts=[],
                new_parts=[],
                new_transforms=[]
            )
        
        # Use LLM to select part and transforms
        tpt_result = self._llm_construct_tpt(
            taxon_resolution, 
            applicable_parts, 
            available_transforms
        )
        
        return TPTConstruction(
            food_id=taxon_resolution.food_id,
            food_name=taxon_resolution.food_name,
            taxon_id=taxon_resolution.taxon_id,
            part_id=tpt_result.get('part_id'),
            transforms=tpt_result.get('transforms', []),
            confidence=tpt_result.get('confidence', 0.0),
            disposition=tpt_result.get('disposition', 'ambiguous'),
            reason=tpt_result.get('reason', ''),
            applicable_parts=applicable_parts,
            new_parts=tpt_result.get('new_parts', []),
            new_transforms=tpt_result.get('new_transforms', [])
        )
    
    def _llm_construct_tpt(self, taxon_resolution: TaxonResolution, 
                          applicable_parts: List[Dict[str, Any]], 
                          available_transforms: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to construct TPT from applicable parts and transforms"""
        
        # Build prompt for TPT construction
        prompt = self._build_tpt_prompt(taxon_resolution, applicable_parts, available_transforms)
        
        try:
            start_time = time.time()
            print(f"[TIER 2] → Constructing TPT for {taxon_resolution.food_name}")
            print(f"[TIER 2] → Available parts: {len(applicable_parts)} applicable")
            print(f"[TIER 2] → Calling LLM ({self.model})...")
            
            response = call_llm(
                model=self.model,
                system=self._get_tpt_system_prompt(),
                user=prompt,
                temperature=0.3
            )
            
            duration = time.time() - start_time
            token_usage = response.get('_token_usage', {})
            print(f"[TIER 2] → LLM Response ({duration:.2f}s, {token_usage.get('total_tokens', 0)} tokens)")
            
            return response
            
        except Exception as e:
            return {
                'part_id': None,
                'transforms': [],
                'confidence': 0.0,
                'disposition': 'skip',
                'reason': f"LLM error: {str(e)}",
                'new_parts': [],
                'new_transforms': []
            }
    
    def _build_tpt_prompt(self, taxon_resolution: TaxonResolution, 
                         applicable_parts: List[Dict[str, Any]], 
                         available_transforms: List[Dict[str, Any]]) -> str:
        """Build prompt for TPT construction"""
        from .optimized_prompts import get_enhanced_tpt_prompt
        return get_enhanced_tpt_prompt(taxon_resolution, applicable_parts, available_transforms)
    
    def _get_tpt_system_prompt(self) -> str:
        """Get system prompt for TPT construction"""
        from .optimized_prompts import get_optimized_tpt_system_prompt
        return get_optimized_tpt_system_prompt()
    
    def construct_batch(self, taxon_resolutions: List[TaxonResolution], 
                       available_parts: List[Dict[str, Any]], 
                       available_transforms: List[Dict[str, Any]]) -> List[TPTConstruction]:
        """Construct TPTs for a batch of taxon resolutions"""
        results = []
        
        for resolution in taxon_resolutions:
            tpt = self.construct_tpt(resolution, available_parts, available_transforms)
            results.append(tpt)
        
        return results
    
    def get_constructed_tpts(self, constructions: List[TPTConstruction]) -> List[TPTConstruction]:
        """Get successfully constructed TPTs"""
        return [t for t in constructions if t.disposition == 'constructed' and t.part_id]
    
    def get_ambiguous_tpts(self, constructions: List[TPTConstruction]) -> List[TPTConstruction]:
        """Get ambiguous TPT constructions"""
        return [t for t in constructions if t.disposition == 'ambiguous']
    
    def get_skipped_tpts(self, constructions: List[TPTConstruction]) -> List[TPTConstruction]:
        """Get skipped TPT constructions"""
        return [t for t in constructions if t.disposition == 'skip']
    
    def summarize_results(self, constructions: List[TPTConstruction]) -> Dict[str, Any]:
        """Summarize TPT construction results"""
        total = len(constructions)
        constructed = len(self.get_constructed_tpts(constructions))
        ambiguous = len(self.get_ambiguous_tpts(constructions))
        skipped = len(self.get_skipped_tpts(constructions))
        
        avg_confidence = sum(t.confidence for t in constructions) / total if total > 0 else 0
        
        # Count transform usage
        transform_usage = {}
        for tpt in constructions:
            for transform in tpt.transforms:
                transform_id = transform.get('id', 'unknown')
                transform_usage[transform_id] = transform_usage.get(transform_id, 0) + 1
        
        return {
            'total': total,
            'constructed': constructed,
            'ambiguous': ambiguous,
            'skipped': skipped,
            'construction_rate': constructed / total if total > 0 else 0,
            'avg_confidence': avg_confidence,
            'transform_usage': transform_usage
        }
