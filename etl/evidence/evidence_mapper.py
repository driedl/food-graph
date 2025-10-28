#!/usr/bin/env python3
"""
3-Tier Evidence Mapping Pipeline

Main pipeline that integrates all three tiers of the evidence mapping system:
- Tier-1: Taxon-only resolver with NCBI verification
- Tier-2: TPT constructor with lineage-based part filtering
- Tier-3: Full curator with overlay system

This replaces the old single-tier map.py system.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .lib.tier1_taxon import Tier1TaxonResolver, TaxonResolution
from .lib.tier2_tpt import Tier2TPTConstructor
from .lib.tier3_curator import Tier3Curator, EvidenceMapping
from .lib.ncbi_resolver import NCBIResolver
from .lib.part_filter import PartFilter
from .lib.nutrient_store import NutrientStore
from .lib.nutrient_mapper import NutrientMapper
from .lib.unmapped_nutrients import UnmappedNutrientCollector
from .tpt_id_utils import generate_tpt_id
from .lib.fdc import load_foundation_foods_json, filter_nutrients_for_foods
from .lib.jsonl import write_jsonl, read_jsonl
from lib.logging import setup_logger, ProgressTracker, MetricsCollector
from lib.config import find_project_root, resolve_path
from .db import GraphDB
from .lib.schema_validator import validate_tpt_construction, ValidationError, ValidationResult

class EvidenceMapper:
    """3-Tier Evidence Mapping Pipeline"""
    
    def __init__(self, graph_db_path: Path, ncbi_db_path: Path, 
                 overlay_dir: Path, model: str = "gpt-5-mini"):
        """Initialize the evidence mapper"""
        self.graph_db_path = graph_db_path
        self.ncbi_db_path = ncbi_db_path
        self.overlay_dir = overlay_dir
        self.model = model
        
        # Find project root and resolve paths
        project_root = find_project_root()
        
        # Initialize components
        self.ncbi_resolver = NCBIResolver(ncbi_db_path)
        self.part_filter = PartFilter(graph_db_path)
        self.nutrient_store = NutrientStore(graph_db_path)
        self.nutrient_mapper = NutrientMapper(resolve_path("data/ontology/nutrients.json", project_root))
        self.unmapped_collector = UnmappedNutrientCollector(resolve_path("data/ontology/_proposals", project_root))
        
        # Initialize tiers
        self.tier1_resolver = Tier1TaxonResolver(self.ncbi_resolver, model)
        self.tier2_constructor = Tier2TPTConstructor(self.part_filter, model)
        self.tier3_curator = Tier3Curator(
            self.tier1_resolver, 
            self.tier2_constructor, 
            self.nutrient_store, 
            overlay_dir, 
            model
        )
        
        # Initialize database
        self.graph_db = GraphDB(graph_db_path)
        self.nutrient_store.create_tables()
        
        # Build ontology indices for validation
        self.parts_index = {p.id: p for p in self.graph_db.parts()}
        self.transforms_index = {}
        for t in self.graph_db.transforms():
            self.transforms_index[t.id] = {
                'id': t.id,
                'name': t.name,
                'identity': t.identity,
                'order': t.order,
                'params': t.params or []
            }
    
    def map_fdc_evidence(self, fdc_dir: Path, output_dir: Path, 
                        limit: int = 0, min_confidence: float = 0.7, 
                        resume: bool = True) -> Dict[str, Any]:
        """
        Map FDC evidence using the 3-tier system
        
        Args:
            fdc_dir: Directory containing FDC data
            output_dir: Output directory for results
            limit: Limit number of foods to process (0 = no limit)
            min_confidence: Minimum confidence threshold for mapping
            resume: Whether to skip already processed foods (resume mode)
            
        Returns:
            Summary of mapping results
        """
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load FDC data
        print("Loading FDC data...")
        
        # Always load all FDC foundation foods (small dataset ~400 foods)
        all_foods = load_foundation_foods_json(fdc_dir, limit=0)  # 0 = no limit
        
        # Apply resume logic if enabled
        if resume:
            existing_foods = self._get_processed_food_ids(output_dir)
            if existing_foods:
                print(f"[RESUME] → Found {len(existing_foods)} already processed foods")
                # Filter out already processed foods
                new_foods = [f for f in all_foods if str(f.get('fdc_id', '')) not in existing_foods]
                print(f"[RESUME] → Found {len(new_foods)} unprocessed foods")
                
                # Apply limit to new foods only
                if limit > 0:
                    foods = new_foods[:limit]
                    print(f"[RESUME] → Processing {len(foods)} new foods (limit: {limit})")
                else:
                    foods = new_foods
                    print(f"[RESUME] → Processing all {len(foods)} new foods")
            else:
                print("[RESUME] → No previously processed foods found")
                # Apply limit to all foods
                if limit > 0:
                    foods = all_foods[:limit]
                    print(f"[RESUME] → Processing {len(foods)} foods (limit: {limit})")
                else:
                    foods = all_foods
                    print(f"[RESUME] → Processing all {len(foods)} foods")
        else:
            # No resume - apply limit to all foods
            if limit > 0:
                foods = all_foods[:limit]
                print(f"Processing {len(foods)} foods (limit: {limit})")
            else:
                foods = all_foods
                print(f"Processing all {len(foods)} foods")
        
        nutrients = filter_nutrients_for_foods(fdc_dir, [str(f.get('fdc_id', '')) for f in foods])
        
        # Group nutrients by food ID
        nutrients_by_food = {}
        for nutrient in nutrients:
            food_id = nutrient.get('fdc_id', '')
            if food_id not in nutrients_by_food:
                nutrients_by_food[food_id] = []
            nutrients_by_food[food_id].append(nutrient)
        
        # Load ontology data
        print("Loading ontology data...")
        parts = self.graph_db.parts()
        transforms = self.graph_db.transforms()
        
        # Map evidence using 3-tier system (sequential processing)
        print(f"Mapping evidence for {len(foods)} foods...")
        
        all_mappings = []
        successful_foods = 0
        failed_foods = 0
        
        for i, food in enumerate(foods, 1):
            food_id = str(food.get('fdc_id', food.get('food_id', '')))
            food_name = food.get('description', food.get('name', ''))
            
            print(f"\n[FOOD {i}/{len(foods)}] → Processing: \"{food_name}\"")
            
            try:
                # Process this food through all tiers sequentially
                mapping = self._process_single_food(food, nutrients_by_food, parts, transforms)
                all_mappings.append(mapping)
                successful_foods += 1
                
                # Write results immediately after each food
                self._save_single_food_result(mapping, output_dir, nutrients_by_food, parts, transforms)
                
                print(f"[FOOD {i}/{len(foods)}] → ✓ Completed: {mapping.disposition} (confidence: {mapping.final_confidence:.2f})")
                
            except Exception as e:
                failed_foods += 1
                print(f"[FOOD {i}/{len(foods)}] → ✗ Failed: {str(e)}")
                # Continue processing other foods
                continue
        
        # Print final summary
        print(f"\n[SUMMARY] → Processing complete:")
        print(f"[SUMMARY] → Successful: {successful_foods}")
        print(f"[SUMMARY] → Failed: {failed_foods}")
        print(f"[SUMMARY] → Total: {len(foods)}")
        
        # Filter by confidence
        filtered_mappings = [m for m in all_mappings if m.final_confidence >= min_confidence]
        
        # Process unmapped nutrients
        print("\n[NUTRIENTS] → Processing unmapped nutrients...")
        unmapped_proposals = self.unmapped_collector.collect_unmapped_nutrients()
        if unmapped_proposals:
            self.unmapped_collector.save_unmapped_proposals(unmapped_proposals)
            self.unmapped_collector.save_unmapped_report(unmapped_proposals)
            print(f"[NUTRIENTS] → Generated {len(unmapped_proposals)} unmapped nutrient proposals")
        else:
            print("[NUTRIENTS] → No unmapped nutrients found")
        
        # Generate summary
        summary = self._generate_summary(all_mappings, filtered_mappings, successful_foods, failed_foods, min_confidence, unmapped_proposals)
        
        return summary
    
    def _process_single_food(self, food: Dict[str, Any], 
                           nutrients_by_food: Dict[str, List[Dict[str, Any]]],
                           parts: List[Any], transforms: List[Any]) -> EvidenceMapping:
        """
        Process a single food through all 3 tiers sequentially
        
        Args:
            food: Food item data
            nutrients_by_food: Nutrient data by food ID
            parts: Available parts from ontology
            transforms: Available transforms from ontology
            
        Returns:
            EvidenceMapping with complete mapping results
        """
        food_id = str(food.get('fdc_id', food.get('food_id', '')))
        food_name = food.get('description', food.get('name', ''))
        food_description = food.get('additional_description', '')
        
        # Tier 1: Taxon resolution
        print(f"[TIER 1] → Resolving taxon for \"{food_name}\"...")
        taxon_resolution = self.tier1_resolver.resolve_taxon(food_id, food_name, food_description)
        
        if taxon_resolution.disposition == 'skip':
            print(f"[TIER 1] → Skipped: {taxon_resolution.reason}")
            return self._create_skipped_mapping(food_id, food_name, taxon_resolution)
        
        if taxon_resolution.disposition == 'ambiguous':
            print(f"[TIER 1] → Ambiguous: {taxon_resolution.reason}")
            return self._create_ambiguous_mapping(food_id, food_name, taxon_resolution)
        
        print(f"[TIER 1] → ✓ Resolved: {taxon_resolution.taxon_id} (confidence: {taxon_resolution.confidence:.2f})")
        
        # Tier 2: TPT construction
        print(f"[TIER 2] → Constructing TPT for \"{food_name}\"...")
        tpt_construction = self.tier2_constructor.construct_tpt(taxon_resolution, parts, transforms)
        
        if tpt_construction.disposition == 'skip':
            print(f"[TIER 2] → Skipped: {tpt_construction.reason}")
            return self._create_skipped_mapping(food_id, food_name, taxon_resolution)
        
        # NEW: Route ambiguous/failed cases to Tier 3 for intelligent decision-making
        if tpt_construction.disposition != 'constructed':
            print(f"[TIER 2] → Failed/Ambiguous: {tpt_construction.reason}")
            print(f"[TIER 3] → Curating ambiguous TPT...")
            
            # Pass failed TPT to Tier 3 for curation (not re-running Tier 1/2)
            mapping = self.tier3_curator.curate_ambiguous_tpt(
                tpt_construction,
                taxon_resolution,
                nutrients_by_food.get(food_id, []),
                parts,
                transforms
            )
            print(f"[TIER 3] → ✓ Curated: {mapping.disposition} (confidence: {mapping.final_confidence:.2f})")
            return mapping
        
        print(f"[TIER 2] → ✓ Constructed: {tpt_construction.part_id} (confidence: {tpt_construction.confidence:.2f})")
        
        # Determine if Tier 3 curation is needed for low confidence
        needs_curation = tpt_construction.confidence < 0.8
        
        if needs_curation:
            print(f"[TIER 3] → Curating low-confidence TPT for \"{food_name}\"...")
            # Use Tier 3 curator for low-confidence cases
            mapping = self.tier3_curator.map_evidence(
                food, nutrients_by_food.get(food_id, []), parts, transforms
            )
            print(f"[TIER 3] → ✓ Curated: {mapping.disposition} (confidence: {mapping.final_confidence:.2f})")
        else:
            # High confidence - create mapping directly
            print(f"[TIER 2] → High confidence, skipping Tier 3")
            mapping = self._create_high_confidence_mapping(food_id, food_name, taxon_resolution, tpt_construction, nutrients_by_food.get(food_id, []))
        
        return mapping
    
    def _create_skipped_mapping(self, food_id: str, food_name: str, taxon_resolution: TaxonResolution) -> EvidenceMapping:
        """Create a mapping for skipped foods"""
        return EvidenceMapping(
            food_id=food_id,
            food_name=food_name,
            taxon_resolution=taxon_resolution,
            tpt_construction=None,
            nutrient_rows=[],
            final_confidence=0.0,
            disposition='skipped',
            reason=f"Taxon resolution skipped: {taxon_resolution.reason}",
            overlay_applied=False
        )
    
    def _create_ambiguous_mapping(self, food_id: str, food_name: str, taxon_resolution: TaxonResolution) -> EvidenceMapping:
        """Create a mapping for ambiguous foods"""
        return EvidenceMapping(
            food_id=food_id,
            food_name=food_name,
            taxon_resolution=taxon_resolution,
            tpt_construction=None,
            nutrient_rows=[],
            final_confidence=taxon_resolution.confidence,
            disposition='ambiguous',
            reason=f"Taxon resolution ambiguous: {taxon_resolution.reason}",
            overlay_applied=False
        )
    
    def _create_failed_mapping(self, food_id: str, food_name: str, taxon_resolution: TaxonResolution, tpt_construction: Any) -> EvidenceMapping:
        """Create a mapping for failed TPT construction"""
        return EvidenceMapping(
            food_id=food_id,
            food_name=food_name,
            taxon_resolution=taxon_resolution,
            tpt_construction=tpt_construction,
            nutrient_rows=[],
            final_confidence=tpt_construction.confidence,
            disposition='failed',
            reason=f"TPT construction failed: {tpt_construction.reason}",
            overlay_applied=False
        )
    
    def _create_high_confidence_mapping(self, food_id: str, food_name: str, taxon_resolution: TaxonResolution, 
                                      tpt_construction: Any, nutrient_data: List[Dict[str, Any]]) -> EvidenceMapping:
        """Create a mapping for high-confidence TPT construction"""
        # Map nutrients for this food
        nutrient_rows, unmapped_nutrients = self.nutrient_store.map_fdc_nutrients_with_mapper(
            nutrient_data, self.nutrient_mapper
        )
        
        # Collect unmapped nutrients for proposals
        for unmapped in unmapped_nutrients:
            self.unmapped_collector.add_unmapped_nutrient(unmapped)
        
        return EvidenceMapping(
            food_id=food_id,
            food_name=food_name,
            taxon_resolution=taxon_resolution,
            tpt_construction=tpt_construction,
            nutrient_rows=nutrient_rows,
            final_confidence=tpt_construction.confidence,
            disposition='mapped',
            reason=f"High confidence TPT construction: {tpt_construction.reason}",
            overlay_applied=False
        )
    
    def _save_single_food_result(self, mapping: EvidenceMapping, output_dir: Path,
                                 nutrients_by_food: Dict[str, List[Dict[str, Any]]],
                                 parts: List[Any], transforms: List[Any]) -> None:
        """Save results for a single food immediately after processing"""
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate TPT construction before generating ID
        tpt_id = None
        disposition = mapping.disposition
        reason = mapping.reason
        confidence = mapping.final_confidence
        
        if mapping.tpt_construction and mapping.tpt_construction.part_id and disposition == 'mapped':
            # Validate schema
            validation_result = validate_tpt_construction(
                mapping.tpt_construction,
                self.parts_index,
                self.transforms_index
            )
            
            if not validation_result.valid:
                # Route to Tier 3 for remediation
                print(f"[VALIDATION] {mapping.food_id} ({mapping.food_name}): {len(validation_result.errors)} error(s) detected")
                print(f"[TIER 3] → Attempting remediation...")
                
                try:
                    # Get nutrient data for this food
                    nutrient_data = nutrients_by_food.get(mapping.food_id, [])
                    
                    # Call Tier 3 remediation
                    remediated_mapping = self.tier3_curator.remediate_validation_errors(
                        tpt_construction=mapping.tpt_construction,
                        validation_errors=validation_result.structured_errors or [],
                        nutrient_data=nutrient_data,
                        available_parts=parts,
                        available_transforms=transforms
                    )
                    
                    # Update mapping with remediation result
                    mapping = remediated_mapping
                    disposition = mapping.disposition
                    reason = mapping.reason
                    confidence = mapping.final_confidence
                    
                    # If remediation succeeded, validate again and generate TPT ID
                    if disposition == 'mapped':
                        revalidation = validate_tpt_construction(
                            mapping.tpt_construction,
                            self.parts_index,
                            self.transforms_index
                        )
                        
                        if revalidation.valid:
                            try:
                                tpt_id = generate_tpt_id(
                                    taxon_id=mapping.tpt_construction.taxon_id,
                                    part_id=mapping.tpt_construction.part_id,
                                    transforms=mapping.tpt_construction.transforms
                                )
                                print(f"[TIER 3] → ✓ Remediation successful: {tpt_id}")
                            except Exception as e:
                                print(f"[WARNING] Failed to generate TPT ID after remediation: {e}")
                                tpt_id = None
                        else:
                            # Remediation didn't fix all errors - reject
                            disposition = 'rejected'
                            confidence = 0.0
                            reason = f"Remediation incomplete: {revalidation.errors[0]}"
                            tpt_id = None
                            print(f"[TIER 3] → ✗ Remediation incomplete")
                    else:
                        # Tier 3 rejected it
                        tpt_id = None
                        print(f"[TIER 3] → Rejected: {reason}")
                        
                except Exception as e:
                    # Remediation failed
                    tpt_id = None
                    disposition = 'rejected'
                    confidence = 0.0
                    reason = f"Remediation error: {str(e)}"
                    print(f"[TIER 3] → ✗ Remediation failed: {str(e)}")
            else:
                # Schema valid, generate TPT ID
                try:
                    tpt_id = generate_tpt_id(
                        taxon_id=mapping.tpt_construction.taxon_id,
                        part_id=mapping.tpt_construction.part_id,
                        transforms=mapping.tpt_construction.transforms
                    )
                except Exception as e:
                    print(f"[WARNING] Failed to generate TPT ID for {mapping.food_id}: {e}")
                    tpt_id = None
        
        # Save evidence mapping
        evidence_data = {
            'food_id': mapping.food_id,
            'food_name': mapping.food_name,
            'taxon_id': mapping.taxon_resolution.taxon_id if mapping.taxon_resolution else None,
            'part_id': mapping.tpt_construction.part_id if mapping.tpt_construction else None,
            'transforms': mapping.tpt_construction.transforms if mapping.tpt_construction else [],
            'tpt_id': tpt_id,
            'confidence': confidence,
            'disposition': disposition,
            'reason': reason,
            'overlay_applied': mapping.overlay_applied
        }
        
        # Append to evidence mappings file
        evidence_file = output_dir / 'evidence_mappings.jsonl'
        with open(evidence_file, 'a') as f:
            f.write(json.dumps(evidence_data) + '\n')
        
        # Save nutrient data if available
        if mapping.nutrient_rows:
            nutrient_data = []
            for nutrient_row in mapping.nutrient_rows:
                nutrient_data.append({
                    'food_id': nutrient_row.food_id,
                    'nutrient_id': nutrient_row.nutrient_id,
                    'amount': nutrient_row.amount,
                    'unit': nutrient_row.unit,
                    'original_amount': nutrient_row.original_amount,
                    'original_unit': nutrient_row.original_unit,
                    'original_nutrient_id': nutrient_row.original_nutrient_id,
                    'conversion_factor': nutrient_row.conversion_factor,
                    'source': nutrient_row.source,
                    'confidence': nutrient_row.confidence,
                    'nutrient_name': nutrient_row.nutrient_name,
                    'nutrient_class': nutrient_row.nutrient_class,
                    'tpt_id': tpt_id
                })
            
            # Append to nutrient data file
            nutrient_file = output_dir / 'nutrient_data.jsonl'
            with open(nutrient_file, 'a') as f:
                for item in nutrient_data:
                    f.write(json.dumps(item) + '\n')
    
    def _generate_summary(self, all_mappings: List[EvidenceMapping], 
                         filtered_mappings: List[EvidenceMapping],
                         successful_foods: int, failed_foods: int,
                         min_confidence: float, unmapped_proposals: List[Any]) -> Dict[str, Any]:
        """Generate summary statistics"""
        total_foods = successful_foods + failed_foods
        
        # Count dispositions
        disposition_counts = {}
        for mapping in all_mappings:
            disp = mapping.disposition
            disposition_counts[disp] = disposition_counts.get(disp, 0) + 1
        
        # Calculate average confidence
        avg_confidence = sum(m.final_confidence for m in all_mappings) / len(all_mappings) if all_mappings else 0
        
        # Add nutrient mapping statistics
        mapping_stats = self.nutrient_mapper.get_mapping_stats()
        
        # Count total nutrients stored across all mappings
        total_nutrients = sum(len(mapping.nutrient_rows) for mapping in all_mappings)
        
        return {
            'total_foods': total_foods,
            'successful_foods': successful_foods,
            'failed_foods': failed_foods,
            'mapped': disposition_counts.get('mapped', 0),
            'ambiguous': disposition_counts.get('ambiguous', 0),
            'skipped': disposition_counts.get('skipped', 0),
            'failed': disposition_counts.get('failed', 0),
            'filtered_mappings': len(filtered_mappings),
            'min_confidence': min_confidence,
            'avg_confidence': avg_confidence,
            'mapping_rate': disposition_counts.get('mapped', 0) / total_foods if total_foods > 0 else 0,
            'unmapped_nutrients': len(unmapped_proposals),
            'total_nutrients': total_nutrients,
            'nutrient_mapping': mapping_stats
        }
    
    def _get_processed_food_ids(self, output_dir: Path) -> set:
        """Get set of already processed food IDs from existing evidence mappings"""
        evidence_file = output_dir / 'evidence_mappings.jsonl'
        if not evidence_file.exists():
            return set()
        
        processed_ids = set()
        try:
            with open(evidence_file, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line.strip())
                        food_id = data.get('food_id', '')
                        if food_id:
                            # The food_id in evidence_mappings.jsonl is already just the FDC ID
                            # (e.g., "321358"), not "fdc:321358"
                            processed_ids.add(food_id)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        
        return processed_ids
    
    def _validate_mapping_consistency(self, mappings: List[Any]) -> None:
        """Validate data consistency across mappings"""
        issues = []
        
        for mapping in mappings:
            # Check for missing taxon resolution
            if not mapping.taxon_resolution and mapping.disposition == 'mapped':
                issues.append(f"Food {mapping.food_id} mapped but missing taxon resolution")
            
            # Check for missing TPT construction
            if not mapping.tpt_construction and mapping.disposition == 'mapped':
                issues.append(f"Food {mapping.food_id} mapped but missing TPT construction")
            
            # Check for orphaned nutrient data
            if mapping.nutrient_rows and not mapping.tpt_construction:
                issues.append(f"Food {mapping.food_id} has nutrient data but no TPT construction")
            
            # Check for inconsistent food IDs
            if mapping.taxon_resolution and mapping.taxon_resolution.food_id != mapping.food_id:
                issues.append(f"Food ID mismatch: mapping={mapping.food_id}, taxon={mapping.taxon_resolution.food_id}")
            
            if mapping.tpt_construction and mapping.tpt_construction.food_id != mapping.food_id:
                issues.append(f"Food ID mismatch: mapping={mapping.food_id}, tpt={mapping.tpt_construction.food_id}")
        
        if issues:
            print(f"[VALIDATION] → Found {len(issues)} consistency issues:")
            for issue in issues:
                print(f"[VALIDATION] → ⚠️  {issue}")
        else:
            print(f"[VALIDATION] → All {len(mappings)} mappings are consistent")
    
    def clear_overlay(self) -> None:
        """Clear all overlay modifications"""
        self.tier3_curator.clear_overlay()
    
    def get_overlay_summary(self) -> Dict[str, Any]:
        """Get summary of overlay modifications"""
        return self.tier3_curator.get_overlay_summary()

def main():
    """Main entry point for evidence mapping"""
    parser = argparse.ArgumentParser(description="3-Tier Evidence Mapping Pipeline")
    parser.add_argument("--graph-db", required=True, type=Path, help="Graph database path")
    parser.add_argument("--ncbi-db", required=True, type=Path, help="NCBI database path")
    parser.add_argument("--fdc-dir", required=True, type=Path, help="FDC data directory")
    parser.add_argument("--output", required=True, type=Path, help="Output directory")
    parser.add_argument("--overlay-dir", default="data/ontology/_overlay", type=Path, help="Overlay directory")
    parser.add_argument("--model", default="gpt-5-mini", help="LLM model to use")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of foods to process")
    parser.add_argument("--min-confidence", type=float, default=0.7, help="Minimum confidence threshold")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Initialize evidence mapper
    mapper = EvidenceMapper(
        graph_db_path=args.graph_db,
        ncbi_db_path=args.ncbi_db,
        overlay_dir=args.overlay_dir,
        model=args.model
    )
    
    # Run mapping
    print("Starting 3-tier evidence mapping...")
    summary = mapper.map_fdc_evidence(
        fdc_dir=args.fdc_dir,
        output_dir=args.output,
        limit=args.limit,
        min_confidence=args.min_confidence
    )
    
    # Print summary
    print("\nMapping Summary:")
    print(f"Total foods processed: {summary['total_foods']}")
    print(f"Successfully mapped: {summary['mapped']}")
    print(f"Ambiguous: {summary['ambiguous']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Mapping rate: {summary['mapping_rate']:.2%}")
    print(f"Average confidence: {summary['avg_confidence']:.2f}")
    print(f"Overlay modifications: {summary.get('overlay_count', 0)}")
    print(f"Total nutrients stored: {summary.get('total_nutrients', 0)}")
    
    print(f"\nResults saved to: {args.output}")

if __name__ == "__main__":
    main()
