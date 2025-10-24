#!/usr/bin/env python3
"""
Stage 1: NCBI Verification Runner

Computes parent relationships from taxon ID structure, verifies NCBI taxonomy IDs,
and enriches taxa with full lineage information for applicability matching.
"""

from __future__ import annotations
import argparse
from pathlib import Path

from graph.io import ensure_dir
from .ncbi_verify import verify_taxa

def run(in_dir: Path, build_dir: Path, verbose: bool = False) -> int:
    """Run Stage 1: NCBI Verification."""
    try:
        # Ensure directories exist
        ensure_dir(build_dir / "tmp")
        
        # Path to NCBI database (should be built separately)
        ncbi_db_path = build_dir / "database" / "ncbi.sqlite"
        
        if not ncbi_db_path.exists():
            print(f"ERROR: NCBI database not found at {ncbi_db_path}")
            print("")
            print("To create the NCBI database, run one of these commands:")
            print("")
            print("  # Option 1: Using pnpm (recommended)")
            print("  pnpm etl:ncbi")
            print("")
            print("  # Option 2: Direct Python command")
            print("  python3 etl/graph/external/ncbi_loader.py --output etl/build/database/ncbi.sqlite")
            print("")
            print("  # Option 3: From the etl directory")
            print("  cd etl && python3 graph/external/ncbi_loader.py --output build/database/ncbi.sqlite")
            print("")
            print("Note: This will download ~100MB of NCBI taxonomy data and may take a few minutes.")
            return 1
        
        # Run NCBI verification
        verify_taxa(
            in_dir=build_dir,  # Use build_dir to find compiled taxa
            tmp_dir=build_dir / "tmp",
            ncbi_db_path=ncbi_db_path,
            verbose=verbose
        )
        
        if verbose:
            print("Stage 1: NCBI verification completed successfully")
        
        return 0
        
    except Exception as e:
        print(f"ERROR in Stage 1: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1

def main():
    parser = argparse.ArgumentParser(description="Stage 1: NCBI Verification")
    parser.add_argument("--in-dir", type=Path, required=True, help="Input directory (build/)")
    parser.add_argument("--build-dir", type=Path, required=True, help="Build directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    exit(run(args.in_dir, args.build_dir, args.verbose))

if __name__ == "__main__":
    main()
