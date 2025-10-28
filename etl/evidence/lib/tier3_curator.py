#!/usr/bin/env python3
"""
Tier-3: Full Curator with Overlay System

Third tier of the 3-tier evidence mapping system. Provides full curation capabilities
with overlay system for temporary ontology modifications and comprehensive evidence mapping.
"""

from __future__ import annotations
import json
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from .tier1_taxon import Tier1TaxonResolver, TaxonResolution
from .tier2_tpt import Tier2TPTConstructor, TPTConstruction
from .ncbi_resolver import NCBIResolver
from .part_filter import PartFilter
from .nutrient_store import NutrientStore, NutrientRow
from .llm import call_llm

@dataclass
class OntologyCuration:
    """Ontology curation recommendations from Tier 3"""
    # Part modifications
    new_parts: List[Dict[str, Any]]  # New parts to add
    modify_parts: List[Dict[str, Any]]  # Existing parts to modify
    part_applies_to_rules: List[Dict[str, Any]]  # New applies_to rules
    
    # Transform modifications  
    new_transforms: List[Dict[str, Any]]  # New transforms to add
    modify_transforms: List[Dict[str, Any]]  # Existing transforms to modify
    transform_param_schemas: List[Dict[str, Any]]  # New parameter schemas
    transform_applicability_rules: List[Dict[str, Any]]  # New transform applicability rules
    
    # Relationship modifications
    derived_part_rules: List[Dict[str, Any]]  # New derived part relationships
    modify_rules: List[Dict[str, Any]]  # Existing rules to modify
    
    # Ontology optimization
    optimization_suggestions: List[str]  # General optimization recommendations
    confidence: float  # Confidence in curation recommendations
    reasoning: str  # Detailed reasoning for all changes

@dataclass
class EvidenceMapping:
    """Complete evidence mapping result"""
    food_id: str
    food_name: str
    taxon_resolution: TaxonResolution
    tpt_construction: TPTConstruction
    nutrient_rows: List[NutrientRow]
    final_confidence: float
    disposition: str  # 'mapped', 'ambiguous', 'skip'
    reason: str
    overlay_applied: bool
    curation: Optional[OntologyCuration] = None  # Tier 3 curation results

class Tier3Curator:
    """Tier-3: Full curator with overlay system"""
    
    def __init__(self, tier1_resolver: Tier1TaxonResolver, 
                 tier2_constructor: Tier2TPTConstructor,
                 nutrient_store: NutrientStore,
                 overlay_dir: Path,
                 model: str = "gpt-5"):
        """Initialize with all components"""
        self.tier1_resolver = tier1_resolver
        self.tier2_constructor = tier2_constructor
        self.nutrient_store = nutrient_store
        self.overlay_dir = overlay_dir
        self.model = model
        
        # Ensure overlay directory exists
        self.overlay_dir.mkdir(parents=True, exist_ok=True)
    
    def curate_ambiguous_tpt(
        self,
        tpt_construction: TPTConstruction,
        taxon_resolution: TaxonResolution,
        nutrient_data: List[Dict[str, Any]],
        available_parts: List[Dict[str, Any]],
        available_transforms: List[Dict[str, Any]]
    ) -> EvidenceMapping:
        """
        Curate an ambiguous/failed TPT from Tier 2 using LLM intelligence.
        
        This is for when Tier 2 couldn't complete a TPT (missing transforms, uncertainty).
        Tier 3 analyzes the partial TPT and decides what to do.
        
        Args:
            tpt_construction: Partial/failed TPT from Tier 2
            taxon_resolution: Taxon resolution from Tier 1
            nutrient_data: Nutrient data for the food
            available_parts: Available parts from ontology
            available_transforms: Available transforms from ontology
            
        Returns:
            EvidenceMapping with curated TPT
        """
        from .optimized_prompts import get_optimized_curation_system_prompt
        
        print(f"[TIER 3] → Curating ambiguous TPT for {tpt_construction.food_name}")
        
        # Build curation prompt for the partial TPT
        prompt = f"Food: {tpt_construction.food_name}\n"
        prompt += f"Taxon: {taxon_resolution.taxon_id}\n"
        prompt += f"Reason: {tpt_construction.reason}\n\n"
        prompt += "Tier 2 constructed a partial TPT but marked it as ambiguous/failed. "
        prompt += "Analyze the issue and determine the best path forward:\n\n"
        
        prompt += "1. Can we complete the TPT despite missing transforms?\n"
        prompt += "2. Should we propose new transforms/parts to the ontology?\n"
        prompt += "3. Is Tier 2 fundamentally wrong and we should reject?\n\n"
        
        prompt += "Return JSON with: {\"strategy\": \"...\", \"corrected_tpt\": {...}, \"overlay_proposal\": {...}, \"reasoning\": \"...\"}\n"
        
        try:
            # Call LLM for curation analysis
            start_time = time.time()
            response = call_llm(
                model=self.model,
                system=get_optimized_curation_system_prompt(),
                user=prompt,
                temperature=0.3
            )
            
            duration = time.time() - start_time
            print(f"[TIER 3] → Curation complete ({duration:.2f}s)")
            
            strategy = response.get('strategy', 'reject')
            corrected_tpt = response.get('corrected_tpt', {})
            reasoning = response.get('reasoning', 'No reasoning')
            confidence = response.get('confidence', 0.7)
            overlay_proposal = response.get('overlay_proposal')
            
            print(f"[TIER 3] → Strategy: {strategy}, Confidence: {confidence:.2f}")
            
            # Apply corrections to TPT
            if corrected_tpt:
                tpt_construction.part_id = corrected_tpt.get('part_id', tpt_construction.part_id)
                tpt_construction.transforms = corrected_tpt.get('transforms', tpt_construction.transforms)
            
            # Handle overlay if proposed
            overlay_applied = False
            if overlay_proposal and strategy == 'expand':
                self._apply_overlay([], [overlay_proposal], [])
                overlay_applied = True
            
            # Map nutrients
            nutrient_mapping = self.nutrient_store.create_nutrient_mapping()
            nutrient_rows = self.nutrient_store.map_fdc_nutrients(nutrient_data, nutrient_mapping)
            
            # Determine final disposition based on strategy
            if strategy in ['complete', 'expand'] and confidence >= 0.7:
                disposition = 'mapped'
            elif confidence >= 0.4:
                disposition = 'ambiguous'
            else:
                disposition = 'rejected'
            
            return EvidenceMapping(
                food_id=tpt_construction.food_id,
                food_name=tpt_construction.food_name,
                taxon_resolution=taxon_resolution,
                tpt_construction=tpt_construction,
                nutrient_rows=nutrient_rows,
                final_confidence=confidence,
                disposition=disposition,
                reason=f"Tier 3 curation ({strategy}): {reasoning}",
                overlay_applied=overlay_applied
            )
            
        except Exception as e:
            print(f"[TIER 3] → Curation failed: {str(e)}")
            # Preserve taxon from function parameter or tpt_construction
            final_taxon_resolution = taxon_resolution
            if not final_taxon_resolution and tpt_construction.taxon_id:
                from .tier1_taxon import TaxonResolution
                final_taxon_resolution = TaxonResolution(
                    food_id=tpt_construction.food_id,
                    food_name=tpt_construction.food_name,
                    taxon_id=tpt_construction.taxon_id,
                    confidence=1.0,
                    disposition='resolved',
                    reason='Preserved from TPT construction',
                    ncbi_resolution=None,
                    new_taxa=[]
                )
            
            return EvidenceMapping(
                food_id=tpt_construction.food_id,
                food_name=tpt_construction.food_name,
                taxon_resolution=final_taxon_resolution,
                tpt_construction=tpt_construction,
                nutrient_rows=[],
                final_confidence=0.0,
                disposition='rejected',
                reason=f"Tier 3 curation error: {str(e)}",
                overlay_applied=False
            )
    
    def remediate_validation_errors(
        self,
        tpt_construction: TPTConstruction,
        validation_errors: List[Any],
        nutrient_data: List[Dict[str, Any]],
        available_parts: List[Dict[str, Any]],
        available_transforms: List[Dict[str, Any]]
    ) -> EvidenceMapping:
        """
        Remediate validation errors using LLM-guided bucketing strategy.
        
        Args:
            tpt_construction: Original TPT from Tier 2 (failed validation)
            validation_errors: List of ValidationError objects
            nutrient_data: Nutrient data for the food
            available_parts: Available parts from ontology
            available_transforms: Available transforms from ontology
            
        Returns:
            EvidenceMapping with corrected TPT or rejection
        """
        from .optimized_prompts import get_remediation_system_prompt, get_remediation_user_prompt
        
        print(f"[TIER 3] → Remediating {len(validation_errors)} validation error(s) for {tpt_construction.food_name}")
        
        # Build remediation prompt
        system_prompt = get_remediation_system_prompt()
        user_prompt = get_remediation_user_prompt(
            tpt_construction.food_name,
            tpt_construction,
            validation_errors
        )
        
        try:
            # Call LLM for remediation
            start_time = time.time()
            response = call_llm(
                model=self.model,
                system=system_prompt,
                user=user_prompt,
                temperature=0.2
            )
            
            duration = time.time() - start_time
            print(f"[TIER 3] → Remediation complete ({duration:.2f}s)")
            
            strategy = response.get('strategy', 'reject')
            corrected_tpt = response.get('corrected_tpt', {})
            reasoning = response.get('reasoning', 'No reasoning provided')
            confidence = response.get('confidence', 0.0)
            overlay_proposal = response.get('overlay_proposal')
            
            print(f"[TIER 3] → Strategy: {strategy}, Confidence: {confidence:.2f}")
            
            # Handle based on strategy
            if strategy == 'map':
                # Apply corrected TPT
                tpt_construction.part_id = corrected_tpt.get('part_id', tpt_construction.part_id)
                tpt_construction.transforms = corrected_tpt.get('transforms', tpt_construction.transforms)
                
                # Map nutrients
                nutrient_mapping = self.nutrient_store.create_nutrient_mapping()
                nutrient_rows = self.nutrient_store.map_fdc_nutrients(nutrient_data, nutrient_mapping)
                
                # Preserve taxon information from tpt_construction
                taxon_resolution = None
                if tpt_construction.taxon_id:
                    from .tier1_taxon import TaxonResolution
                    taxon_resolution = TaxonResolution(
                        food_id=tpt_construction.food_id,
                        food_name=tpt_construction.food_name,
                        taxon_id=tpt_construction.taxon_id,
                        confidence=1.0,
                        disposition='resolved',
                        reason='Preserved from Tier 2',
                        ncbi_resolution=None,
                        new_taxa=[]
                    )
                
                return EvidenceMapping(
                    food_id=tpt_construction.food_id,
                    food_name=tpt_construction.food_name,
                    taxon_resolution=taxon_resolution,
                    tpt_construction=tpt_construction,
                    nutrient_rows=nutrient_rows,
                    final_confidence=confidence,
                    disposition='mapped',
                    reason=f"Tier 3 remediation (map): {reasoning}",
                    overlay_applied=False
                )
            
            elif strategy == 'expand':
                # Propose overlay expansion
                if overlay_proposal:
                    self._apply_overlay([], [overlay_proposal], [])
                
                # Apply corrected TPT
                tpt_construction.part_id = corrected_tpt.get('part_id', tpt_construction.part_id)
                tpt_construction.transforms = corrected_tpt.get('transforms', tpt_construction.transforms)
                
                # Map nutrients
                nutrient_mapping = self.nutrient_store.create_nutrient_mapping()
                nutrient_rows = self.nutrient_store.map_fdc_nutrients(nutrient_data, nutrient_mapping)
                
                # Preserve taxon information from tpt_construction
                taxon_resolution = None
                if tpt_construction.taxon_id:
                    from .tier1_taxon import TaxonResolution
                    taxon_resolution = TaxonResolution(
                        food_id=tpt_construction.food_id,
                        food_name=tpt_construction.food_name,
                        taxon_id=tpt_construction.taxon_id,
                        confidence=1.0,
                        disposition='resolved',
                        reason='Preserved from Tier 2',
                        ncbi_resolution=None,
                        new_taxa=[]
                    )
                
                return EvidenceMapping(
                    food_id=tpt_construction.food_id,
                    food_name=tpt_construction.food_name,
                    taxon_resolution=taxon_resolution,
                    tpt_construction=tpt_construction,
                    nutrient_rows=nutrient_rows,
                    final_confidence=confidence,
                    disposition='mapped',
                    reason=f"Tier 3 remediation (expand): {reasoning}",
                    overlay_applied=True
                )
            
            else:  # reject
                # Preserve taxon information from tpt_construction
                taxon_resolution = None
                if tpt_construction.taxon_id:
                    from .tier1_taxon import TaxonResolution
                    taxon_resolution = TaxonResolution(
                        food_id=tpt_construction.food_id,
                        food_name=tpt_construction.food_name,
                        taxon_id=tpt_construction.taxon_id,
                        confidence=1.0,
                        disposition='resolved',
                        reason='Preserved from Tier 2',
                        ncbi_resolution=None,
                        new_taxa=[]
                    )
                
                return EvidenceMapping(
                    food_id=tpt_construction.food_id,
                    food_name=tpt_construction.food_name,
                    taxon_resolution=taxon_resolution,
                    tpt_construction=tpt_construction,
                    nutrient_rows=[],
                    final_confidence=0.0,
                    disposition='rejected',
                    reason=f"Tier 3 remediation (reject): {reasoning}",
                    overlay_applied=False
                )
        
        except Exception as e:
            print(f"[TIER 3] → Remediation failed: {str(e)}")
            # Preserve taxon information from tpt_construction on error
            error_taxon_resolution = None
            if tpt_construction.taxon_id:
                from .tier1_taxon import TaxonResolution
                error_taxon_resolution = TaxonResolution(
                    food_id=tpt_construction.food_id,
                    food_name=tpt_construction.food_name,
                    taxon_id=tpt_construction.taxon_id,
                    confidence=1.0,
                    disposition='resolved',
                    reason='Preserved from Tier 2',
                    ncbi_resolution=None,
                    new_taxa=[]
                )
            
            return EvidenceMapping(
                food_id=tpt_construction.food_id,
                food_name=tpt_construction.food_name,
                taxon_resolution=error_taxon_resolution,
                tpt_construction=tpt_construction,
                nutrient_rows=[],
                final_confidence=0.0,
                disposition='rejected',
                reason=f"Tier 3 remediation error: {str(e)}",
                overlay_applied=False
            )
    
    def map_evidence(self, food_data: Dict[str, Any], 
                    nutrient_data: List[Dict[str, Any]],
                    available_parts: List[Dict[str, Any]], 
                    available_transforms: List[Dict[str, Any]]) -> EvidenceMapping:
        """
        Map evidence for a food item using the full 3-tier system
        
        Args:
            food_data: Food item data
            nutrient_data: Nutrient data for the food
            available_parts: Available parts from ontology
            available_transforms: Available transforms from ontology
            
        Returns:
            EvidenceMapping with complete mapping results
        """
        food_id = food_data.get('fdc_id', food_data.get('food_id', ''))
        food_name = food_data.get('description', food_data.get('name', ''))
        
        # Tier-1: Taxon resolution
        taxon_resolution = self.tier1_resolver.resolve_taxon(
            food_id, food_name, food_data.get('additional_description', '')
        )
        
        # Tier-2: TPT construction
        tpt_construction = self.tier2_constructor.construct_tpt(
            taxon_resolution, available_parts, available_transforms
        )
        
        # Handle overlay system for new taxa/parts/transforms
        overlay_applied = False
        if taxon_resolution.new_taxa or tpt_construction.new_parts or tpt_construction.new_transforms:
            overlay_applied = self._apply_overlay(
                taxon_resolution.new_taxa,
                tpt_construction.new_parts,
                tpt_construction.new_transforms
            )
        
        # Store nutrient data
        nutrient_mapping = self.nutrient_store.create_nutrient_mapping()
        nutrient_rows = self.nutrient_store.map_fdc_nutrients(nutrient_data, nutrient_mapping)
        
        # Calculate final confidence
        final_confidence = self._calculate_final_confidence(
            taxon_resolution, tpt_construction, nutrient_rows
        )
        
        # Determine final disposition
        disposition = self._determine_final_disposition(
            taxon_resolution, tpt_construction, final_confidence
        )
        
        # Generate final reason
        reason = self._generate_final_reason(
            taxon_resolution, tpt_construction, final_confidence, overlay_applied
        )
        
        return EvidenceMapping(
            food_id=food_id,
            food_name=food_name,
            taxon_resolution=taxon_resolution,
            tpt_construction=tpt_construction,
            nutrient_rows=nutrient_rows,
            final_confidence=final_confidence,
            disposition=disposition,
            reason=reason,
            overlay_applied=overlay_applied
        )
    
    def _apply_overlay(self, new_taxa: List[Dict[str, Any]], 
                      new_parts: List[Dict[str, Any]], 
                      new_transforms: List[Dict[str, Any]]) -> bool:
        """Apply overlay modifications to ontology"""
        applied = False
        
        # Apply new taxa
        if new_taxa:
            self._write_overlay_file('taxa.jsonl', new_taxa)
            applied = True
        
        # Apply new parts
        if new_parts:
            print(f"[TIER 3] → Proposing {len(new_parts)} new parts via overlay")
            for part in new_parts:
                print(f"[TIER 3] → New part: {part.get('id', 'unknown')} - {part.get('reason', 'no reason')}")
            self._write_overlay_file('parts.jsonl', new_parts)
            applied = True
        
        # Apply new transforms
        if new_transforms:
            self._write_overlay_file('transforms.jsonl', new_transforms)
            applied = True
            
        # Apply transform applicability rules
        if new_transforms:
            # Extract applicability rules from new transforms that have them
            applicability_rules = []
            for transform in new_transforms:
                if 'applies_to' in transform:
                    applicability_rules.append({
                        "transform": transform['id'],
                        "applies_to": transform['applies_to']
                    })
            if applicability_rules:
                self._write_overlay_file('transform_applicability.jsonl', applicability_rules)
                applied = True
        
        return applied
    
    def _write_overlay_file(self, filename: str, data: List[Dict[str, Any]]) -> None:
        """Write overlay data to file"""
        overlay_file = self.overlay_dir / filename
        
        # Append to existing overlay file or create new one
        with open(overlay_file, 'a', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    def _calculate_final_confidence(self, taxon_resolution: TaxonResolution, 
                                  tpt_construction: TPTConstruction, 
                                  nutrient_rows: List[NutrientRow]) -> float:
        """Calculate final confidence score"""
        # Base confidence from taxon resolution
        base_confidence = taxon_resolution.confidence
        
        # Adjust based on TPT construction
        if tpt_construction.disposition == 'constructed':
            base_confidence = min(base_confidence + 0.1, 1.0)
        elif tpt_construction.disposition == 'ambiguous':
            base_confidence = max(base_confidence - 0.1, 0.0)
        else:  # skip
            base_confidence = max(base_confidence - 0.2, 0.0)
        
        # Adjust based on nutrient data quality
        if nutrient_rows:
            avg_nutrient_confidence = sum(row.confidence for row in nutrient_rows) / len(nutrient_rows)
            base_confidence = (base_confidence + avg_nutrient_confidence) / 2
        
        return base_confidence
    
    def _determine_final_disposition(self, taxon_resolution: TaxonResolution, 
                                   tpt_construction: TPTConstruction, 
                                   final_confidence: float) -> str:
        """Determine final disposition"""
        if taxon_resolution.disposition == 'skip' or tpt_construction.disposition == 'skip':
            return 'skip'
        elif final_confidence >= 0.7:
            return 'mapped'
        elif final_confidence >= 0.4:
            return 'ambiguous'
        else:
            return 'skip'
    
    def _generate_final_reason(self, taxon_resolution: TaxonResolution, 
                             tpt_construction: TPTConstruction, 
                             final_confidence: float, 
                             overlay_applied: bool) -> str:
        """Generate final reason for mapping"""
        reasons = []
        
        if taxon_resolution.reason:
            reasons.append(f"Taxon: {taxon_resolution.reason}")
        
        if tpt_construction.reason:
            reasons.append(f"TPT: {tpt_construction.reason}")
        
        if overlay_applied:
            reasons.append("Overlay modifications applied")
        
        reasons.append(f"Final confidence: {final_confidence:.2f}")
        
        return "; ".join(reasons)
    
    def map_batch(self, foods_data: List[Dict[str, Any]], 
                  nutrients_data: Dict[str, List[Dict[str, Any]]],
                  available_parts: List[Dict[str, Any]], 
                  available_transforms: List[Dict[str, Any]]) -> List[EvidenceMapping]:
        """Map evidence for a batch of foods"""
        results = []
        
        for food_data in foods_data:
            food_id = food_data.get('fdc_id', food_data.get('food_id', ''))
            nutrient_data = nutrients_data.get(food_id, [])
            
            mapping = self.map_evidence(food_data, nutrient_data, available_parts, available_transforms)
            results.append(mapping)
        
        return results
    
    def curate_tier2_results(self, tier2_tpts: List[Any], 
                           nutrients_data: Dict[str, List[Dict[str, Any]]],
                           available_parts: List[Dict[str, Any]], 
                           available_transforms: List[Dict[str, Any]]) -> List[EvidenceMapping]:
        """
        Curate Tier 2 TPT results with comprehensive ontology evolution capabilities.
        This is the sophisticated curator that can modify the entire ontology structure.
        
        Args:
            tier2_tpts: List of TPTConstruction results from Tier 2
            nutrients_data: Nutrient data by food ID
            available_parts: Available parts from ontology
            available_transforms: Available transforms from ontology
            
        Returns:
            List of curated EvidenceMapping results with ontology curation
        """
        results = []
        
        for tpt in tier2_tpts:
            food_id = tpt.food_id
            food_name = tpt.food_name
            nutrient_data = nutrients_data.get(food_id, [])
            
            print(f"[TIER 3] → Curating {food_name} (confidence: {tpt.confidence:.2f})")
            
            # Perform comprehensive ontology curation
            curation = self._perform_ontology_curation(
                tpt, available_parts, available_transforms, nutrients_data.get(food_id, [])
            )
            
            # Apply curation recommendations
            curated_tpt = self._apply_curation_recommendations(tpt, curation)
            overlay_applied = self._apply_overlay_from_curation(curation)
            
            # Map nutrients (preserve existing mapping unless TPT changed significantly)
            nutrient_mapping = self.nutrient_store.create_nutrient_mapping()
            nutrient_rows = self.nutrient_store.map_fdc_nutrients(nutrient_data, nutrient_mapping)
            
            # Calculate final confidence
            final_confidence = self._calculate_final_confidence(
                None,  # No taxon resolution needed (already done in Tier 2)
                curated_tpt, 
                nutrient_rows
            )
            
            # Determine final disposition
            if final_confidence >= 0.7:
                disposition = 'mapped'
            elif final_confidence >= 0.4:
                disposition = 'ambiguous'
            else:
                disposition = 'skip'
            
            # Preserve taxon information from tpt construction
            curation_taxon_resolution = None
            if curated_tpt.taxon_id:
                from .tier1_taxon import TaxonResolution
                curation_taxon_resolution = TaxonResolution(
                    food_id=food_id,
                    food_name=food_name,
                    taxon_id=curated_tpt.taxon_id,
                    confidence=1.0,
                    disposition='resolved',
                    reason='Preserved from curation',
                    ncbi_resolution=None,
                    new_taxa=[]
                )
            
            # Create evidence mapping with curation results
            mapping = EvidenceMapping(
                food_id=food_id,
                food_name=food_name,
                taxon_resolution=curation_taxon_resolution,
                tpt_construction=curated_tpt,
                nutrient_rows=nutrient_rows,
                final_confidence=final_confidence,
                disposition=disposition,
                reason=f"Tier 3 curation: {curation.reasoning}",
                overlay_applied=overlay_applied,
                curation=curation
            )
            
            results.append(mapping)
        
        return results
    
    def _perform_ontology_curation(self, tpt: Any, available_parts: List[Dict[str, Any]], 
                                 available_transforms: List[Dict[str, Any]], 
                                 nutrient_data: List[Dict[str, Any]]) -> OntologyCuration:
        """
        Perform comprehensive ontology curation using LLM analysis.
        This is the core curation logic that evaluates all aspects of the ontology.
        """
        # Build comprehensive curation prompt
        prompt = self._build_curation_prompt(tpt, available_parts, available_transforms, nutrient_data)
        
        # Call LLM for curation analysis
        try:
            start_time = time.time()
            print(f"[TIER 3] → Calling LLM ({self.model}) for ontology curation...")
            
            response = call_llm(
                model=self.model,
                system=self._get_curation_system_prompt(),
                user=prompt,
                temperature=0.3
            )
            
            duration = time.time() - start_time
            token_usage = response.get('_token_usage', {})
            print(f"[TIER 3] → LLM Response ({duration:.2f}s, {token_usage.get('total_tokens', 0)} tokens)")
            
            # Parse LLM response into curation recommendations
            curation = self._parse_curation_response(response)
            
            return curation
            
        except Exception as e:
            print(f"[TIER 3] → LLM error: {str(e)}")
            return OntologyCuration(
                new_parts=[],
                modify_parts=[],
                part_applies_to_rules=[],
                new_transforms=[],
                modify_transforms=[],
                transform_param_schemas=[],
                derived_part_rules=[],
                modify_rules=[],
                optimization_suggestions=[],
                confidence=0.0,
                reasoning=f"LLM error: {str(e)}"
            )
    
    def _build_curation_prompt(self, tpt: Any, available_parts: List[Dict[str, Any]], 
                             available_transforms: List[Dict[str, Any]], 
                             nutrient_data: List[Dict[str, Any]]) -> str:
        """Build comprehensive curation prompt for LLM analysis"""
        prompt = f"Food: {tpt.food_name}\n"
        prompt += f"Taxon: {tpt.taxon_id}\n"
        prompt += f"Proposed Part: {tpt.part_id}\n"
        prompt += f"Proposed Transforms: {[t.get('id') for t in tpt.transforms]}\n"
        prompt += f"Confidence: {tpt.confidence:.2f}\n"
        prompt += f"Disposition: {tpt.disposition}\n"
        prompt += f"Reason: {tpt.reason}\n\n"
        
        # Add context about available parts and transforms
        prompt += "Available Parts (sample):\n"
        for part in available_parts[:10]:  # Show sample
            prompt += f"  {part.get('id')}: {part.get('name')} (kind: {part.get('kind')})\n"
        
        prompt += "\nAvailable Transforms (sample):\n"
        for transform in available_transforms[:10]:  # Show sample
            prompt += f"  {transform.get('id')}: {transform.get('name')}\n"
        
        prompt += "\nNutrient Data (sample):\n"
        for nutrient in nutrient_data[:5]:  # Show sample
            prompt += f"  {nutrient.get('nutrient_id')}: {nutrient.get('amount')} {nutrient.get('unit')}\n"
        
        prompt += "\nAnalyze this food mapping and provide comprehensive ontology curation recommendations."
        
        return prompt
    
    def _get_curation_system_prompt(self) -> str:
        """Get system prompt for comprehensive ontology curation"""
        from .optimized_prompts import get_optimized_curation_system_prompt
        return get_optimized_curation_system_prompt()
    
    def _parse_curation_response(self, response: Dict[str, Any]) -> OntologyCuration:
        """Parse LLM response into OntologyCuration object"""
        return OntologyCuration(
            new_parts=response.get('new_parts', []),
            modify_parts=response.get('modify_parts', []),
            part_applies_to_rules=response.get('part_applies_to_rules', []),
            new_transforms=response.get('new_transforms', []),
            modify_transforms=response.get('modify_transforms', []),
            transform_param_schemas=response.get('transform_param_schemas', []),
            derived_part_rules=response.get('derived_part_rules', []),
            modify_rules=response.get('modify_rules', []),
            optimization_suggestions=response.get('optimization_suggestions', []),
            confidence=response.get('confidence', 0.0),
            reasoning=response.get('reasoning', 'No reasoning provided')
        )
    
    def _apply_curation_recommendations(self, tpt: Any, curation: OntologyCuration) -> Any:
        """Apply curation recommendations to the TPT construction"""
        # For now, return the original TPT
        # In a full implementation, this would apply the curation recommendations
        # and potentially modify the TPT construction
        return tpt
    
    def _apply_overlay_from_curation(self, curation: OntologyCuration) -> bool:
        """Apply overlay changes based on curation recommendations"""
        # Check if any curation recommendations require overlay application
        has_changes = (
            curation.new_parts or
            curation.modify_parts or
            curation.new_transforms or
            curation.modify_transforms or
            curation.derived_part_rules
        )
        
        if has_changes:
            # Apply overlay for new parts/transforms
            self._apply_overlay(
                [],  # No new taxa from curation
                curation.new_parts,
                curation.new_transforms
            )
            return True
        
        return False
    
    def get_mapped_evidence(self, mappings: List[EvidenceMapping]) -> List[EvidenceMapping]:
        """Get successfully mapped evidence"""
        return [m for m in mappings if m.disposition == 'mapped']
    
    def get_ambiguous_evidence(self, mappings: List[EvidenceMapping]) -> List[EvidenceMapping]:
        """Get ambiguous evidence mappings"""
        return [m for m in mappings if m.disposition == 'ambiguous']
    
    def get_skipped_evidence(self, mappings: List[EvidenceMapping]) -> List[EvidenceMapping]:
        """Get skipped evidence mappings"""
        return [m for m in mappings if m.disposition == 'skip']
    
    def summarize_results(self, mappings: List[EvidenceMapping]) -> Dict[str, Any]:
        """Summarize mapping results"""
        total = len(mappings)
        mapped = len(self.get_mapped_evidence(mappings))
        ambiguous = len(self.get_ambiguous_evidence(mappings))
        skipped = len(self.get_skipped_evidence(mappings))
        
        avg_confidence = sum(m.final_confidence for m in mappings) / total if total > 0 else 0
        
        # Count overlay usage
        overlay_count = sum(1 for m in mappings if m.overlay_applied)
        
        # Count nutrient data
        total_nutrients = sum(len(m.nutrient_rows) for m in mappings)
        avg_nutrients = total_nutrients / total if total > 0 else 0
        
        return {
            'total': total,
            'mapped': mapped,
            'ambiguous': ambiguous,
            'skipped': skipped,
            'mapping_rate': mapped / total if total > 0 else 0,
            'avg_confidence': avg_confidence,
            'overlay_count': overlay_count,
            'total_nutrients': total_nutrients,
            'avg_nutrients_per_food': avg_nutrients
        }
    
    def clear_overlay(self) -> None:
        """Clear all overlay modifications"""
        if self.overlay_dir.exists():
            shutil.rmtree(self.overlay_dir)
        self.overlay_dir.mkdir(parents=True, exist_ok=True)
    
    def get_overlay_summary(self) -> Dict[str, Any]:
        """Get summary of overlay modifications"""
        overlay_files = list(self.overlay_dir.glob('*.jsonl'))
        
        summary = {
            'overlay_files': len(overlay_files),
            'files': {}
        }
        
        for overlay_file in overlay_files:
            with open(overlay_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            summary['files'][overlay_file.name] = {
                'count': len(lines),
                'size_bytes': overlay_file.stat().st_size
            }
        
        return summary
