#!/usr/bin/env python3
"""
Comprehensive Nutrient Mapping System

Maps FDC nutrient data to canonical INFOODS format using nutrients.json as source of truth.
Handles unit conversions, stores both original and converted values, and flags unmapped nutrients.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class NutrientMapping:
    """FDC to INFOODS nutrient mapping"""
    fdc_id: str
    infoods_id: str
    fdc_unit: str
    infoods_unit: str
    conversion_factor: float
    confidence: str
    nutrient_name: str
    class_: str

@dataclass
class MappedNutrient:
    """Result of mapping a single FDC nutrient"""
    mapped: bool
    nutrient_row: Optional[Any] = None  # NutrientRow object
    unmapped_info: Optional[UnmappedNutrientInfo] = None

@dataclass
class UnmappedNutrientInfo:
    """Information about an unmapped nutrient"""
    fdc_id: str
    fdc_name: str
    fdc_unit: str
    food_id: str
    amount: float

class NutrientMapper:
    """Comprehensive FDC-to-INFOODS nutrient mapping system"""
    
    def __init__(self, nutrients_json_path: Path):
        """Initialize with nutrients.json path"""
        self.nutrients_json_path = nutrients_json_path
        self.nutrients_data = self._load_nutrients()
        self.fdc_to_infoods_mapping = self._build_fdc_to_infoods_mapping()
        self.unmapped_nutrients: List[UnmappedNutrientInfo] = []
    
    def _load_nutrients(self) -> Dict[str, Any]:
        """Load nutrients.json data"""
        with open(self.nutrients_json_path, 'r') as f:
            return json.load(f)
    
    def _build_fdc_to_infoods_mapping(self) -> Dict[str, NutrientMapping]:
        """Build comprehensive FDC to INFOODS mapping from nutrients.json"""
        mapping = {}
        
        for nutrient in self.nutrients_data['nutrients']:
            infoods_id = nutrient['id']
            infoods_unit = nutrient['unit']
            fdc_unit = nutrient.get('fdc_unit', '')
            conversion_factor = nutrient.get('unit_factor_from_fdc', 1.0)
            confidence = nutrient.get('confidence', 'medium')
            nutrient_name = nutrient['name']
            class_ = nutrient['class']
            
            # Map all FDC candidates for this nutrient
            fdc_candidates = nutrient.get('fdc_candidates', [])
            for fdc_id in fdc_candidates:
                mapping[fdc_id] = NutrientMapping(
                    fdc_id=fdc_id,
                    infoods_id=infoods_id,
                    fdc_unit=fdc_unit,
                    infoods_unit=infoods_unit,
                    conversion_factor=conversion_factor,
                    confidence=confidence,
                    nutrient_name=nutrient_name,
                    class_=class_
                )
        
        return mapping
    
    def map_fdc_nutrient(self, fdc_nutrient: Dict[str, Any]) -> MappedNutrient:
        """Map a single FDC nutrient to canonical format"""
        fdc_id = str(fdc_nutrient.get('nutrient_id', ''))
        food_id = fdc_nutrient.get('fdc_id', fdc_nutrient.get('food_id', ''))
        amount = float(fdc_nutrient.get('amount', 0))
        unit = fdc_nutrient.get('unit', 'g')
        
        # Check if we have a mapping for this FDC nutrient ID
        if fdc_id in self.fdc_to_infoods_mapping:
            mapping = self.fdc_to_infoods_mapping[fdc_id]
            
            # Apply unit conversion
            converted_amount = amount * mapping.conversion_factor
            
            # Create nutrient row data (will be converted to NutrientRow by caller)
            nutrient_row_data = {
                'id': f"{food_id}_{mapping.infoods_id}",
                'food_id': food_id,
                'nutrient_id': mapping.infoods_id,
                'amount': converted_amount,
                'unit': mapping.infoods_unit,
                'original_amount': amount,
                'original_unit': unit,
                'original_nutrient_id': fdc_id,
                'conversion_factor': mapping.conversion_factor,
                'source': 'fdc_foundation',
                'confidence': 0.9 if mapping.confidence == 'high' else 0.7,
                'notes': f"FDC nutrient: {fdc_id} -> {mapping.infoods_id}",
                'nutrient_name': mapping.nutrient_name,
                'nutrient_class': mapping.class_
            }
            
            return MappedNutrient(mapped=True, nutrient_row=nutrient_row_data)
        else:
            # No mapping found - flag for manual curation
            unmapped_info = UnmappedNutrientInfo(
                fdc_id=fdc_id,
                fdc_name=fdc_nutrient.get('name', f'FDC_{fdc_id}'),
                fdc_unit=unit,
                food_id=food_id,
                amount=amount
            )
            self.unmapped_nutrients.append(unmapped_info)
            
            return MappedNutrient(mapped=False, unmapped_info=unmapped_info)
    
    def get_unmapped_nutrients(self) -> List[UnmappedNutrientInfo]:
        """Get all unmapped nutrients for manual curation"""
        return self.unmapped_nutrients
    
    def get_mapping_stats(self) -> Dict[str, Any]:
        """Get statistics about the mapping"""
        total_fdc_ids = len(self.fdc_to_infoods_mapping)
        unmapped_count = len(self.unmapped_nutrients)
        
        # Count by confidence level
        confidence_counts = {}
        for mapping in self.fdc_to_infoods_mapping.values():
            conf = mapping.confidence
            confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
        
        return {
            'total_fdc_ids_mapped': total_fdc_ids,
            'unmapped_nutrients': unmapped_count,
            'confidence_breakdown': confidence_counts,
            'nutrients_json_version': self.nutrients_data.get('version', 'unknown')
        }
    
    def validate_mappings(self) -> List[str]:
        """Validate all mappings for consistency"""
        issues = []
        
        for fdc_id, mapping in self.fdc_to_infoods_mapping.items():
            # Check if the INFOODS ID exists in nutrients.json
            infoods_exists = any(n['id'] == mapping.infoods_id for n in self.nutrients_data['nutrients'])
            if not infoods_exists:
                issues.append(f"FDC {fdc_id} maps to non-existent INFOODS ID: {mapping.infoods_id}")
            
            # Check unit conversion factor is reasonable
            if mapping.conversion_factor <= 0 or mapping.conversion_factor > 1000:
                issues.append(f"FDC {fdc_id} has suspicious conversion factor: {mapping.conversion_factor}")
        
        return issues
