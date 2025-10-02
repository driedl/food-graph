from __future__ import annotations
import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Optional
import yaml

from .validators import run_validators

def verify(stage: str, in_dir: Path, build_dir: Path, verbose: bool = False) -> int:
    """Verify a stage's contract and return 0 for success, 1 for failure"""
    # Handle stage naming: stage_0 -> stage_0, stage_a -> stage_a, etc.
    # Path: etl2/mise/contracts/engine.py -> etl2/mise/stages/stage_X/
    stage_dir = Path(__file__).resolve().parents[1] / "stages" / stage
    contract_path = stage_dir / "contract.yml"
    
    report_dir = build_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"verify_{stage}.json"

    errors: list[str] = []
    
    # Load and run contract validators
    try:
        if contract_path.exists():
            spec = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
            errs = run_validators(spec or {}, build_dir)
            errors.extend(errs)
        else:
            errors.append(f"contract file not found: {contract_path}")
    except Exception as e:
        errors.append(f"contract error: {e}")
        if verbose:
            traceback.print_exc()

    # Run optional extra checks
    extra_py = stage_dir / "extra_checks.py"
    if extra_py.exists():
        try:
            mod = _load_module(extra_py)
            extra_errs = mod.run(in_dir=in_dir, build_dir=build_dir) or []
            errors.extend(extra_errs)
        except Exception as e:
            errors.append(f"extra_checks error: {e}")
            if verbose:
                traceback.print_exc()

    # Write report
    report = {
        "stage": stage,
        "errors": errors,
        "ok": len(errors) == 0,
        "error_count": len(errors)
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Print results
    if errors:
        print(f"✗ Verify {stage}: {len(errors)} issue(s) — see {report_path}")
        if verbose:
            for e in errors:
                print("  -", e)
        return 1
    else:
        print(f"✓ Verify {stage}: OK")
        return 0

def _load_module(path: Path):
    """Dynamically load a Python module from a file path"""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if not spec or not spec.loader:
        raise ImportError(f"Could not load module from {path}")
    
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
