#!/usr/bin/env python3
"""
Tier-1: Taxon-Only Resolver

First tier of the 3-tier evidence mapping system. Focuses solely on taxon resolution
using NCBI verification and LLM-based taxon identification.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .ncbi_resolver import NCBIResolver, NCBIResolution
from .llm import call_llm, DEFAULT_SYSTEM

@dataclass
class TaxonResolution:
    """Result of Tier-1 taxon resolution"""
    food_id: str
    food_name: str
    taxon_id: Optional[str]
    confidence: float
    disposition: str  # 'resolved', 'ambiguous', 'skip'
    reason: str
    ncbi_resolution: Optional[NCBIResolution]
    new_taxa: List[Dict[str, Any]]

class Tier1TaxonResolver:
    """Tier-1: Taxon-only resolver with NCBI verification"""
    
    def __init__(self, ncbi_resolver: NCBIResolver, model: str = "gpt-5-mini"):
        """Initialize with NCBI resolver and LLM model"""
        self.ncbi_resolver = ncbi_resolver
        self.model = model
    
    def resolve_taxon(self, food_id: str, food_name: str, food_description: str = "") -> TaxonResolution:
        """
        Resolve taxon for a food item using LLM + NCBI verification
        
        Args:
            food_id: FDC food ID
            food_name: Food name/description
            food_description: Additional food description
            
        Returns:
            TaxonResolution with taxon identification results
        """
        # Build prompt for taxon resolution
        prompt = self._build_taxon_prompt(food_name, food_description)
        
        # Call LLM for taxon resolution
        try:
            start_time = time.time()
            print(f"[TIER 1] Processing: \"{food_name}\"")
            print(f"[TIER 1] → Calling LLM ({self.model})...")
            
            response = call_llm(
                model=self.model,
                system=self._get_taxon_system_prompt(),
                user=prompt,
                temperature=0.3
            )
            
            duration = time.time() - start_time
            token_usage = response.get('_token_usage', {})
            print(f"[TIER 1] → LLM Response ({duration:.2f}s, {token_usage.get('total_tokens', 0)} tokens)")
            
            # Parse LLM response
            taxon_id = response.get('taxon_id')
            confidence = response.get('confidence', 0.0)
            disposition = response.get('disposition', 'ambiguous')
            reason = response.get('reason', '')
            new_taxa = response.get('new_taxa', [])
            
            # Verify with NCBI if we have a taxon ID
            ncbi_resolution = None
            if taxon_id and taxon_id != 'null':
                ncbi_resolution = self.ncbi_resolver.resolve_taxon(taxon_id)
                
                # Adjust confidence based on NCBI verification
                if ncbi_resolution.ncbi_taxid and ncbi_resolution.confidence > 0.5:
                    confidence = min(confidence + 0.1, 1.0)
                    reason += f" (NCBI verified: {ncbi_resolution.reason})"
                elif ncbi_resolution.needs_refinement:
                    confidence = max(confidence - 0.2, 0.0)
                    reason += f" (NCBI needs refinement: {ncbi_resolution.reason})"
                else:
                    confidence = max(confidence - 0.3, 0.0)
                    reason += f" (NCBI not found: {ncbi_resolution.reason})"
            
            # Determine final disposition
            if disposition == 'skip':
                final_disposition = 'skip'
            elif confidence >= 0.7:
                final_disposition = 'resolved'
            elif confidence >= 0.4:
                final_disposition = 'ambiguous'
            else:
                final_disposition = 'skip'
            
            return TaxonResolution(
                food_id=food_id,
                food_name=food_name,
                taxon_id=taxon_id if final_disposition != 'skip' else None,
                confidence=confidence,
                disposition=final_disposition,
                reason=reason,
                ncbi_resolution=ncbi_resolution,
                new_taxa=new_taxa
            )
            
        except Exception as e:
            return TaxonResolution(
                food_id=food_id,
                food_name=food_name,
                taxon_id=None,
                confidence=0.0,
                disposition='skip',
                reason=f"LLM error: {str(e)}",
                ncbi_resolution=None,
                new_taxa=[]
            )
    
    def _build_taxon_prompt(self, food_name: str, food_description: str = "") -> str:
        """Build prompt for taxon resolution"""
        from .optimized_prompts import get_enhanced_taxon_prompt
        return get_enhanced_taxon_prompt(food_name, food_description)
    
    def _get_taxon_system_prompt(self) -> str:
        """Get system prompt for taxon resolution"""
        from .optimized_prompts import get_optimized_taxon_system_prompt
        return get_optimized_taxon_system_prompt()
    
    def resolve_batch(self, foods: List[Dict[str, Any]]) -> List[TaxonResolution]:
        """Resolve taxa for a batch of foods"""
        results = []
        
        for food in foods:
            food_id = str(food.get('fdc_id', food.get('food_id', '')))
            food_name = food.get('description', food.get('name', ''))
            food_description = food.get('additional_description', '')
            
            resolution = self.resolve_taxon(food_id, food_name, food_description)
            results.append(resolution)
        
        return results
    
    def get_resolved_taxa(self, resolutions: List[TaxonResolution]) -> List[TaxonResolution]:
        """Get only successfully resolved taxa"""
        return [r for r in resolutions if r.disposition == 'resolved' and r.taxon_id]
    
    def get_ambiguous_taxa(self, resolutions: List[TaxonResolution]) -> List[TaxonResolution]:
        """Get ambiguous taxon resolutions"""
        return [r for r in resolutions if r.disposition == 'ambiguous']
    
    def get_skipped_taxa(self, resolutions: List[TaxonResolution]) -> List[TaxonResolution]:
        """Get skipped taxon resolutions"""
        return [r for r in resolutions if r.disposition == 'skip']
    
    def summarize_results(self, resolutions: List[TaxonResolution]) -> Dict[str, Any]:
        """Summarize resolution results"""
        total = len(resolutions)
        resolved = len(self.get_resolved_taxa(resolutions))
        ambiguous = len(self.get_ambiguous_taxa(resolutions))
        skipped = len(self.get_skipped_taxa(resolutions))
        
        avg_confidence = sum(r.confidence for r in resolutions) / total if total > 0 else 0
        
        return {
            'total': total,
            'resolved': resolved,
            'ambiguous': ambiguous,
            'skipped': skipped,
            'resolution_rate': resolved / total if total > 0 else 0,
            'avg_confidence': avg_confidence
        }
