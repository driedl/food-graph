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
from .db import GraphDB

class EvidenceMapper:
    """3-Tier Evidence Mapping Pipeline"""
    
    def __init__(self, graph_db_path: Path, ncbi_db_path: Path, 
                 overlay_dir: Path, model: str = "gpt-5-mini"):
        """Initialize the evidence mapper"""
        self.graph_db_path = graph_db_path
        self.ncbi_db_path = ncbi_db_path
        self.overlay_dir = overlay_dir
        self.model = model
        
        # Initialize components
        self.ncbi_resolver = NCBIResolver(ncbi_db_path)
        self.part_filter = PartFilter(graph_db_path)
        self.nutrient_store = NutrientStore(graph_db_path)
        self.nutrient_mapper = NutrientMapper(Path("data/ontology/nutrients.json"))
        self.unmapped_collector = UnmappedNutrientCollector(Path("data/ontology/_proposals"))
        
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
        foods = load_foundation_foods_json(fdc_dir, limit=limit)
        
        # Apply resume logic if enabled
        if resume:
            existing_foods = self._get_processed_food_ids(output_dir)
            if existing_foods:
                print(f"[RESUME] → Found {len(existing_foods)} already processed foods")
                foods = [f for f in foods if str(f.get('fdc_id', '')) not in existing_foods]
                print(f"[RESUME] → Processing {len(foods)} new foods")
            else:
                print("[RESUME] → No previously processed foods found, processing all")
        
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
        
        # Map evidence using 3-tier system
        print(f"Mapping evidence for {len(foods)} foods...")
        print(f"[TIER 1] → Starting taxon resolution...")
        
        # Tier 1: Resolve taxa
        taxon_resolutions = self.tier1_resolver.resolve_batch(foods)
        resolved_taxa = self.tier1_resolver.get_resolved_taxa(taxon_resolutions)
        skipped_taxa = self.tier1_resolver.get_skipped_taxa(taxon_resolutions)
        
        print(f"[TIER 1] → Resolved {len(resolved_taxa)} taxa, skipped {len(skipped_taxa)}")
        
        # Tier 2: Construct TPTs for resolved taxa
        print(f"[TIER 2] → Constructing TPTs for {len(resolved_taxa)} resolved taxa...")
        tpt_constructions = []
        for resolution in resolved_taxa:
            tpt = self.tier2_constructor.construct_tpt(resolution, parts, transforms)
            tpt_constructions.append(tpt)
        
        # Separate high-confidence from low-confidence TPTs
        high_confidence_tpts = [tpt for tpt in tpt_constructions if tpt.confidence >= 0.8 and tpt.disposition == 'constructed']
        low_confidence_tpts = [tpt for tpt in tpt_constructions if tpt.confidence < 0.8 or tpt.disposition != 'constructed']
        
        print(f"[TIER 2] → High confidence: {len(high_confidence_tpts)}, Low confidence: {len(low_confidence_tpts)}")
        
        # Tier 3: Only for low-confidence cases that need curation
        tier3_mappings = []
        if low_confidence_tpts:
            print(f"[TIER 3] → Curating {len(low_confidence_tpts)} low-confidence cases...")
            # Use the new curation method that preserves Tier 2 results
            tier3_mappings = self.tier3_curator.curate_tier2_results(
                low_confidence_tpts, nutrients_by_food, parts, transforms
            )
        
        # Combine high-confidence TPTs with Tier 3 results
        all_mappings = []
        
        # Add high-confidence TPTs as direct mappings
        for tpt in high_confidence_tpts:
            # Map nutrients for this food using comprehensive mapper
            food_id = tpt.food_id
            nutrient_data = nutrients_by_food.get(food_id, [])
            nutrient_rows, unmapped_nutrients = self.nutrient_store.map_fdc_nutrients_with_mapper(
                nutrient_data, self.nutrient_mapper
            )
            
            # Collect unmapped nutrients for proposals
            for unmapped in unmapped_nutrients:
                self.unmapped_collector.add_unmapped_nutrient(unmapped)
            
            # Create evidence mapping
            mapping = EvidenceMapping(
                food_id=tpt.food_id,
                food_name=tpt.food_name,
                taxon_resolution=TaxonResolution(
                    food_id=tpt.food_id,
                    food_name=tpt.food_name,
                    taxon_id=tpt.taxon_id,
                    confidence=0.9,  # High confidence from Tier 2
                    disposition='resolved',
                    reason=f"High confidence TPT construction: {tpt.reason}",
                    ncbi_resolution=None,
                    new_taxa=[]
                ),
                tpt_construction=tpt,
                nutrient_rows=nutrient_rows,
                final_confidence=tpt.confidence,
                disposition='mapped',
                reason=f"Direct TPT mapping: {tpt.reason}",
                overlay_applied=False
            )
            all_mappings.append(mapping)
        
        # Add Tier 3 results
        all_mappings.extend(tier3_mappings)
        
        # Validate data consistency
        self._validate_mapping_consistency(all_mappings)
        
        # Filter by confidence
        filtered_mappings = [m for m in all_mappings if m.final_confidence >= min_confidence]
        
        # Process unmapped nutrients
        print("[NUTRIENTS] → Processing unmapped nutrients...")
        unmapped_proposals = self.unmapped_collector.collect_unmapped_nutrients()
        if unmapped_proposals:
            self.unmapped_collector.save_unmapped_proposals(unmapped_proposals)
            self.unmapped_collector.save_unmapped_report(unmapped_proposals)
            print(f"[NUTRIENTS] → Generated {len(unmapped_proposals)} unmapped nutrient proposals")
        else:
            print("[NUTRIENTS] → No unmapped nutrients found")
        
        # Save results
        self._save_results(filtered_mappings, output_dir)
        
        # Generate summary
        summary = self.tier3_curator.summarize_results(filtered_mappings)
        summary['total_foods'] = len(foods)
        summary['filtered_mappings'] = len(filtered_mappings)
        summary['min_confidence'] = min_confidence
        summary['unmapped_nutrients'] = len(unmapped_proposals)
        
        # Add nutrient mapping statistics
        mapping_stats = self.nutrient_mapper.get_mapping_stats()
        summary['nutrient_mapping'] = mapping_stats
        
        return summary
    
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
                            # Extract FDC ID from food_id (format: fdc:12345)
                            if food_id.startswith('fdc:'):
                                fdc_id = food_id.split(':', 1)[1]
                                processed_ids.add(fdc_id)
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
    
    def _save_results(self, mappings: List[Any], output_dir: Path) -> None:
        """Save mapping results to files (append mode for resume support)"""
        # Save evidence mappings
        evidence_data = []
        for mapping in mappings:
            # Generate canonical TPT ID if available
            tpt_id = None
            if mapping.tpt_construction and mapping.tpt_construction.part_id:
                try:
                    tpt_id = generate_tpt_id(
                        taxon_id=mapping.tpt_construction.taxon_id,
                        part_id=mapping.tpt_construction.part_id,
                        transforms=mapping.tpt_construction.transforms,
                        family="evidence"
                    )
                except Exception as e:
                    print(f"[WARNING] Failed to generate TPT ID for {mapping.food_id}: {e}")
                    tpt_id = None
            
            evidence_data.append({
                'food_id': mapping.food_id,
                'food_name': mapping.food_name,
                'taxon_id': mapping.taxon_resolution.taxon_id,
                'part_id': mapping.tpt_construction.part_id,
                'transforms': mapping.tpt_construction.transforms,
                'tpt_id': tpt_id,
                'confidence': mapping.final_confidence,
                'disposition': mapping.disposition,
                'reason': mapping.reason,
                'overlay_applied': mapping.overlay_applied
            })
        
        # Append to existing file (resume support)
        evidence_file = output_dir / 'evidence_mappings.jsonl'
        with open(evidence_file, 'a') as f:
            for item in evidence_data:
                f.write(json.dumps(item) + '\n')
        
        # Build mapping from food_id to tpt_id for nutrient data
        food_to_tpt = {}
        for mapping in mappings:
            if mapping.tpt_construction and mapping.tpt_construction.part_id:
                try:
                    tpt_id = generate_tpt_id(
                        taxon_id=mapping.tpt_construction.taxon_id,
                        part_id=mapping.tpt_construction.part_id,
                        transforms=mapping.tpt_construction.transforms,
                        family="evidence"
                    )
                    food_to_tpt[mapping.food_id] = tpt_id
                except Exception as e:
                    print(f"[WARNING] Failed to generate TPT ID for nutrient mapping {mapping.food_id}: {e}")
                    continue
        
        # Save nutrient data (append mode)
        nutrient_data = []
        for mapping in mappings:
            for nutrient_row in mapping.nutrient_rows:
                # Add TPT ID if available
                tpt_id = food_to_tpt.get(nutrient_row.food_id)
                
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
        
        # Append to existing file (resume support)
        nutrient_file = output_dir / 'nutrient_data.jsonl'
        with open(nutrient_file, 'a') as f:
            for item in nutrient_data:
                f.write(json.dumps(item) + '\n')
        
        # Save overlay summary
        overlay_summary = self.tier3_curator.get_overlay_summary()
        with open(output_dir / 'overlay_summary.json', 'w') as f:
            json.dump(overlay_summary, f, indent=2)
        
        # Save detailed results
        detailed_results = []
        for mapping in mappings:
            detailed_results.append({
                'food_id': mapping.food_id,
                'food_name': mapping.food_name,
                'taxon_resolution': {
                    'taxon_id': mapping.taxon_resolution.taxon_id,
                    'confidence': mapping.taxon_resolution.confidence,
                    'disposition': mapping.taxon_resolution.disposition,
                    'reason': mapping.taxon_resolution.reason,
                    'ncbi_taxid': mapping.taxon_resolution.ncbi_resolution.ncbi_taxid if mapping.taxon_resolution.ncbi_resolution else None
                },
                'tpt_construction': {
                    'part_id': mapping.tpt_construction.part_id,
                    'transforms': mapping.tpt_construction.transforms,
                    'confidence': mapping.tpt_construction.confidence,
                    'disposition': mapping.tpt_construction.disposition,
                    'reason': mapping.tpt_construction.reason
                },
                'nutrient_count': len(mapping.nutrient_rows),
                'final_confidence': mapping.final_confidence,
                'disposition': mapping.disposition,
                'reason': mapping.reason,
                'overlay_applied': mapping.overlay_applied
            })
        
        write_jsonl(output_dir / 'detailed_results.jsonl', detailed_results)
    
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
    print(f"Overlay modifications: {summary['overlay_count']}")
    print(f"Total nutrients stored: {summary['total_nutrients']}")
    
    print(f"\nResults saved to: {args.output}")

if __name__ == "__main__":
    main()
