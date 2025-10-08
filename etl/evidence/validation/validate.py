#!/usr/bin/env python3
"""
Evidence validation runner

Validates evidence files using the contract system, similar to ETL stage validation.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to Python path for absolute imports
import os
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import yaml

# Try absolute imports first, fall back to relative
try:
    from etl.lib.validators import run_validators
    from etl.evidence.validation.validators import _apply_evidence_jsonl_validators, _apply_evidence_json_validators
except ImportError:
    # Fall back to relative imports when running from etl directory
    from lib.validators import run_validators
    from .validators import _apply_evidence_jsonl_validators, _apply_evidence_json_validators


def validate_evidence(evidence_dir: Path, build_dir: Path, verbose: bool = False) -> int:
    """Validate evidence files using contract system"""
    
    # Load contract
    contract_path = Path(__file__).parent / "contract.yml"
    if not contract_path.exists():
        print(f"ERROR: Contract file not found: {contract_path}")
        return 1
    
    try:
        with contract_path.open("r", encoding="utf-8") as f:
            spec = yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Failed to load contract: {e}")
        return 1
    
    # Create report directory
    report_dir = build_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "evidence_validation.json"
    
    # Run validation
    errors: List[str] = []
    
    # Use evidence-specific validators for JSONL files
    for art in spec.get("artifacts", []):
        path = evidence_dir / art["path"]
        if art.get("must_exist", True) and not path.exists():
            errors.append(f"missing: {art['path']}")
            continue
        
        t = art.get("type", "jsonl")
        if t == "jsonl":
            try:
                try:
                    from etl.lib.validators import _read_jsonl
                except ImportError:
                    from lib.validators import _read_jsonl
                lines = _read_jsonl(path)
                
                # Check line count constraints
                if "min_lines" in art and len(lines) < art["min_lines"]:
                    errors.append(f"{art['path']}: min_lines {art['min_lines']} not met (got {len(lines)})")
                if "max_lines" in art and len(lines) > art["max_lines"]:
                    errors.append(f"{art['path']}: max_lines {art['max_lines']} exceeded (got {len(lines)})")
                
                # Apply evidence-specific validators
                errors.extend(_apply_evidence_jsonl_validators(path, lines, art.get("validators", []), build_dir))
                
            except Exception as e:
                errors.append(f"{art['path']}: read error: {e}")
        elif t == "json":
            try:
                obj = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
                errors.extend(_apply_evidence_json_validators(path, obj, art.get("validators", []), build_dir))
            except Exception as e:
                errors.append(f"{art['path']}: read error: {e}")
    
    # Write report
    report = {
        "evidence_dir": str(evidence_dir),
        "build_dir": str(build_dir),
        "errors": errors,
        "ok": len(errors) == 0,
        "error_count": len(errors)
    }
    
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    
    # Print results
    if errors:
        print(f"✗ Evidence validation failed: {len(errors)} issue(s) — see {report_path}")
        if verbose:
            for error in errors:
                print("  -", error)
        return 1
    else:
        print(f"✓ Evidence validation passed — see {report_path}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Validate evidence files")
    parser.add_argument("--evidence", required=True, help="Path to evidence directory")
    parser.add_argument("--build", default="etl/build", help="Path to build directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    evidence_dir = Path(args.evidence)
    if not evidence_dir.exists():
        print(f"ERROR: Evidence directory not found: {evidence_dir}")
        sys.exit(1)
    
    build_dir = Path(args.build)
    build_dir.mkdir(parents=True, exist_ok=True)
    
    exit_code = validate_evidence(evidence_dir, build_dir, args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
