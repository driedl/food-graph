from __future__ import annotations
import time
from pathlib import Path
from typing import Dict, Any, Tuple

from etl.evidence.load_evidence import load_evidence_to_db
from etl.evidence.compute_rollup import compute_nutrient_rollups
from .contract import verify_stage_g_contract

def run(
    in_dir: Path,
    build_dir: Path,
    verbose: bool = False,
    with_tests: bool = False,
    **kwargs # Catch-all for extra args
) -> Tuple[int, Dict[str, Any]]:
    """
    Stage G: Load evidence data and compute nutrient profile rollups.
    """
    start_time = time.time()
    db_path = build_dir / "database" / "graph.dev.sqlite"
    evidence_base_dir = Path("data/evidence")
    source_quality_config = in_dir / "source_quality.json"

    if not evidence_base_dir.exists():
        print(f"  Skipping Stage G: Evidence base directory {evidence_base_dir} not found.")
        return 0, {}

    print(f"  Loading evidence into {db_path}...")
    load_stats = load_evidence_to_db(evidence_base_dir, db_path, verbose)
    print(f"  Loaded {load_stats['sources_loaded']} sources, {load_stats['mappings_loaded']} mappings, {load_stats['nutrient_rows_loaded']} nutrient rows.")

    print(f"  Computing nutrient profile rollups...")
    rollup_stats = compute_nutrient_rollups(db_path, source_quality_config, verbose)
    print(f"  Computed {rollup_stats['profiles_computed']} nutrient rollups.")

    duration_ms = (time.time() - start_time) * 1000
    
    if with_tests:
        print("  Running Stage G contract verification...")
        verify_stage_g_contract(build_dir, verbose)
        print("  Stage G contract verification passed.")

    return 0, {
        "duration_ms": duration_ms,
        **load_stats,
        **rollup_stats
    }
