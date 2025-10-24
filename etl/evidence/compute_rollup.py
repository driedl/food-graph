from __future__ import annotations
import sqlite3
import json
import statistics
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from .db_utils import get_db_connection, create_rollup_stats, log_stats

def compute_nutrient_rollups(
    graph_db_path: Path,
    source_quality_config: Path,
    verbose: bool = False
) -> Dict[str, int]:
    """Compute nutrient profile rollups from evidence data"""
    
    if verbose:
        print(f"  • Computing nutrient profile rollups...")
    
    # Load source quality configuration
    source_quality = _load_source_quality_config(source_quality_config)
    
    stats = create_rollup_stats()
    
    with get_db_connection(graph_db_path, verbose) as con:
        # Clear existing rollups
        con.execute("DELETE FROM nutrient_profile_rollup")
        
        # Get all nutrient data grouped by (tpt_id, nutrient_id)
        cursor = con.execute("""
            SELECT 
                tpt_id, 
                nutrient_id, 
                amount, 
                unit, 
                source, 
                confidence,
                nutrient_name,
                nutrient_class
            FROM nutrient_row 
            WHERE tpt_id IS NOT NULL 
            ORDER BY tpt_id, nutrient_id
        """)
        
        # Group by (tpt_id, nutrient_id)
        grouped_data = {}
        for row in cursor.fetchall():
            tpt_id, nutrient_id, amount, unit, source, confidence, nutrient_name, nutrient_class = row
            
            key = (tpt_id, nutrient_id)
            if key not in grouped_data:
                grouped_data[key] = {
                    'unit': unit,
                    'nutrient_name': nutrient_name,
                    'nutrient_class': nutrient_class,
                    'values': []
                }
            
            # Calculate weight based on source quality and confidence
            weight = _calculate_weight(source, confidence, source_quality)
            
            grouped_data[key]['values'].append({
                'amount': amount,
                'weight': weight,
                'source': source,
                'confidence': confidence
            })
        
        # Compute rollups for each group
        tpts_processed = set()
        
        for (tpt_id, nutrient_id), data in grouped_data.items():
            tpts_processed.add(tpt_id)
            
            try:
                # Extract values and weights
                values = [v['amount'] for v in data['values']]
                weights = [v['weight'] for v in data['values']]
                
                if not values:
                    stats['skipped_groups'] += 1
                    continue
                
                # Compute weighted median
                weighted_median = _weighted_median(values, weights)
                
                # Compute statistics
                min_value = min(values)
                max_value = max(values)
                source_count = len(values)
                
                # Overall confidence (weighted average)
                total_weight = sum(weights)
                if total_weight > 0:
                    weighted_confidence = sum(w * v['confidence'] for w, v in zip(weights, data['values'])) / total_weight
                else:
                    weighted_confidence = 0.0
                
                # Insert rollup
                con.execute("""
                    INSERT INTO nutrient_profile_rollup (
                        tpt_id, nutrient_id, value, unit, source_count, 
                        min_value, max_value, confidence, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tpt_id,
                    nutrient_id,
                    weighted_median,
                    data['unit'],
                    source_count,
                    min_value,
                    max_value,
                    weighted_confidence,
                    datetime.now(timezone.utc).isoformat()
                ))
                
                stats['profiles_computed'] += 1
                
            except Exception as e:
                if verbose:
                    print(f"    - Warning: Error computing rollup for {tpt_id}, {nutrient_id}: {e}")
                stats['validation_errors'] += 1
                continue
        
        stats['tpts_processed'] = len(tpts_processed)
        con.commit()
    
    log_stats(stats, "Rollup Computation", verbose)
    return stats

def _load_source_quality_config(config_path: Path) -> Dict[str, Any]:
    """Load source quality configuration"""
    
    if not config_path.exists():
        # Return default configuration if file doesn't exist
        return {
            'tiers': {
                'fdc_foundation': {'tier': 1, 'weight': 1.0},
                'canadian_nf': {'tier': 1, 'weight': 1.0},
                'euro_food': {'tier': 1, 'weight': 1.0},
                'fdc_sr_legacy': {'tier': 2, 'weight': 0.9},
                'fdc_branded': {'tier': 3, 'weight': 0.6}
            },
            'default_tier': {'tier': 4, 'weight': 0.5}
        }
    
    with open(config_path, 'r') as f:
        return json.load(f)

def _calculate_weight(source: str, confidence: float, source_quality: Dict[str, Any]) -> float:
    """Calculate weight for a nutrient value based on source quality and confidence"""
    
    # Get source tier configuration
    tiers = source_quality.get('tiers', {})
    source_config = tiers.get(source, source_quality.get('default_tier', {'weight': 0.5}))
    
    base_weight = source_config.get('weight', 0.5)
    
    # Apply per-method modifiers if available
    per_method_modifiers = source_config.get('per_method_modifiers', {})
    # For now, we don't have method information in the nutrient data
    # This could be extended if we add method tracking
    
    # Final weight = base_weight * confidence
    return base_weight * confidence

def _weighted_median(values: List[float], weights: List[float]) -> float:
    """Calculate weighted median of values"""
    
    if not values or not weights or len(values) != len(weights):
        return 0.0
    
    if len(values) == 1:
        return values[0]
    
    # Sort by values while keeping weights aligned
    sorted_pairs = sorted(zip(values, weights))
    sorted_values, sorted_weights = zip(*sorted_pairs)
    
    # Calculate cumulative weights
    total_weight = sum(sorted_weights)
    target_weight = total_weight / 2.0
    
    cumulative_weight = 0.0
    for i, (value, weight) in enumerate(zip(sorted_values, sorted_weights)):
        cumulative_weight += weight
        if cumulative_weight >= target_weight:
            return value
    
    # Fallback to regular median if weighted calculation fails
    return statistics.median(values)
