#!/usr/bin/env python3
"""
Unmapped Nutrient Proposal System

Handles unmapped FDC nutrients for manual curation, similar to food mapping proposals.
Creates structured proposals that can be reviewed and merged into the ontology.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import defaultdict, Counter

@dataclass
class UnmappedNutrient:
    """Unmapped nutrient proposal for manual curation"""
    fdc_id: str
    fdc_name: str
    fdc_unit: str
    occurrence_count: int  # How many foods have this nutrient
    sample_food_ids: List[str]  # Sample foods that have this nutrient
    suggested_action: str  # "map", "ignore", "review"
    confidence: str  # "high", "medium", "low" based on occurrence patterns
    notes: Optional[str] = None

class UnmappedNutrientCollector:
    """Collects and manages unmapped nutrient proposals"""
    
    def __init__(self, proposals_dir: Path):
        """Initialize with proposals directory"""
        self.proposals_dir = proposals_dir
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        self.unmapped_nutrients: List[UnmappedNutrientInfo] = []
    
    def add_unmapped_nutrient(self, unmapped_info: 'UnmappedNutrientInfo') -> None:
        """Add an unmapped nutrient to the collection"""
        self.unmapped_nutrients.append(unmapped_info)
    
    def collect_unmapped_nutrients(self) -> List[UnmappedNutrient]:
        """Process collected unmapped nutrients and create proposals"""
        # Group by FDC ID to count occurrences
        fdc_groups = defaultdict(list)
        for unmapped in self.unmapped_nutrients:
            fdc_groups[unmapped.fdc_id].append(unmapped)
        
        proposals = []
        for fdc_id, unmapped_list in fdc_groups.items():
            # Count occurrences and collect sample foods
            occurrence_count = len(unmapped_list)
            sample_food_ids = list(set(u.food_id for u in unmapped_list))[:5]  # First 5 unique foods
            
            # Determine suggested action based on occurrence patterns
            if occurrence_count >= 10:
                suggested_action = "map"  # High occurrence - likely important
                confidence = "high"
            elif occurrence_count >= 3:
                suggested_action = "review"  # Medium occurrence - worth reviewing
                confidence = "medium"
            else:
                suggested_action = "ignore"  # Low occurrence - might be noise
                confidence = "low"
            
            # Use the most common name and unit
            name_counter = Counter(u.fdc_name for u in unmapped_list)
            unit_counter = Counter(u.fdc_unit for u in unmapped_list)
            most_common_name = name_counter.most_common(1)[0][0]
            most_common_unit = unit_counter.most_common(1)[0][0]
            
            proposal = UnmappedNutrient(
                fdc_id=fdc_id,
                fdc_name=most_common_name,
                fdc_unit=most_common_unit,
                occurrence_count=occurrence_count,
                sample_food_ids=sample_food_ids,
                suggested_action=suggested_action,
                confidence=confidence,
                notes=f"Found in {occurrence_count} foods. Most common name: {most_common_name}, unit: {most_common_unit}"
            )
            proposals.append(proposal)
        
        # Sort by occurrence count (descending)
        proposals.sort(key=lambda x: x.occurrence_count, reverse=True)
        return proposals
    
    def save_unmapped_proposals(self, proposals: List[UnmappedNutrient]) -> None:
        """Save unmapped nutrient proposals to JSONL file"""
        proposals_file = self.proposals_dir / "unmapped_nutrients.jsonl"
        
        with open(proposals_file, 'w') as f:
            for proposal in proposals:
                f.write(json.dumps({
                    'fdc_id': proposal.fdc_id,
                    'fdc_name': proposal.fdc_name,
                    'fdc_unit': proposal.fdc_unit,
                    'occurrence_count': proposal.occurrence_count,
                    'sample_food_ids': proposal.sample_food_ids,
                    'suggested_action': proposal.suggested_action,
                    'confidence': proposal.confidence,
                    'notes': proposal.notes
                }) + '\n')
        
        print(f"Saved {len(proposals)} unmapped nutrient proposals to {proposals_file}")
    
    def generate_unmapped_report(self, proposals: List[UnmappedNutrient]) -> str:
        """Generate a human-readable report of unmapped nutrients"""
        report_lines = [
            "# Unmapped Nutrient Report",
            f"Generated: {Path().cwd()}",
            f"Total unmapped nutrients: {len(proposals)}",
            "",
            "## Summary by Action",
        ]
        
        # Group by suggested action
        action_groups = defaultdict(list)
        for proposal in proposals:
            action_groups[proposal.suggested_action].append(proposal)
        
        for action, action_proposals in action_groups.items():
            report_lines.append(f"### {action.upper()} ({len(action_proposals)} nutrients)")
            for proposal in action_proposals[:10]:  # Show top 10
                report_lines.append(f"- FDC {proposal.fdc_id}: {proposal.fdc_name} ({proposal.fdc_unit}) - {proposal.occurrence_count} occurrences")
            if len(action_proposals) > 10:
                report_lines.append(f"  ... and {len(action_proposals) - 10} more")
            report_lines.append("")
        
        # High-priority nutrients (high occurrence, high confidence)
        high_priority = [p for p in proposals if p.suggested_action == "map" and p.confidence == "high"]
        if high_priority:
            report_lines.extend([
                "## High-Priority Nutrients (Recommended for Mapping)",
                "These nutrients appear frequently and should be prioritized for mapping:",
                ""
            ])
            for proposal in high_priority[:20]:  # Top 20
                report_lines.append(f"- **FDC {proposal.fdc_id}**: {proposal.fdc_name} ({proposal.fdc_unit})")
                report_lines.append(f"  - Occurrences: {proposal.occurrence_count}")
                report_lines.append(f"  - Sample foods: {', '.join(proposal.sample_food_ids[:3])}")
                report_lines.append("")
        
        return "\n".join(report_lines)
    
    def save_unmapped_report(self, proposals: List[UnmappedNutrient]) -> None:
        """Save human-readable report to file"""
        report_file = self.proposals_dir / "unmapped_nutrients_report.md"
        report_content = self.generate_unmapped_report(proposals)
        
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        print(f"Saved unmapped nutrient report to {report_file}")
    
    def load_existing_proposals(self) -> List[UnmappedNutrient]:
        """Load existing unmapped nutrient proposals"""
        proposals_file = self.proposals_dir / "unmapped_nutrients.jsonl"
        
        if not proposals_file.exists():
            return []
        
        proposals = []
        with open(proposals_file, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line.strip())
                    proposal = UnmappedNutrient(
                        fdc_id=data['fdc_id'],
                        fdc_name=data['fdc_name'],
                        fdc_unit=data['fdc_unit'],
                        occurrence_count=data['occurrence_count'],
                        sample_food_ids=data['sample_food_ids'],
                        suggested_action=data['suggested_action'],
                        confidence=data['confidence'],
                        notes=data.get('notes')
                    )
                    proposals.append(proposal)
        
        return proposals
    
    def merge_proposals(self, new_proposals: List[UnmappedNutrient]) -> List[UnmappedNutrient]:
        """Merge new proposals with existing ones, updating occurrence counts"""
        existing_proposals = self.load_existing_proposals()
        existing_by_id = {p.fdc_id: p for p in existing_proposals}
        
        merged_proposals = []
        
        # Process new proposals
        for new_proposal in new_proposals:
            if new_proposal.fdc_id in existing_by_id:
                # Merge with existing proposal
                existing = existing_by_id[new_proposal.fdc_id]
                existing.occurrence_count += new_proposal.occurrence_count
                existing.sample_food_ids.extend(new_proposal.sample_food_ids)
                existing.sample_food_ids = list(set(existing.sample_food_ids))[:10]  # Keep top 10
                
                # Update confidence and action based on new occurrence count
                if existing.occurrence_count >= 10:
                    existing.suggested_action = "map"
                    existing.confidence = "high"
                elif existing.occurrence_count >= 3:
                    existing.suggested_action = "review"
                    existing.confidence = "medium"
                
                merged_proposals.append(existing)
            else:
                # New proposal
                merged_proposals.append(new_proposal)
        
        # Add any existing proposals that weren't updated
        for existing in existing_proposals:
            if existing.fdc_id not in [p.fdc_id for p in new_proposals]:
                merged_proposals.append(existing)
        
        # Sort by occurrence count
        merged_proposals.sort(key=lambda x: x.occurrence_count, reverse=True)
        return merged_proposals
