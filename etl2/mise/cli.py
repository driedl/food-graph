#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mise CLI — Stage runner

Usage:
  python etl2/mise/cli.py run A --in data/ontology --build etl2/build
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

# Local imports
from mise.stages.stage_a.schema_loader import ensure_dir, write_json, write_jsonl
from mise.stages.stage_a.transform_canon import load_and_canonicalize_transforms
from mise.stages.stage_a.rules_normalize import normalize_transform_applicability
from mise.stages.stage_a.flags_validate import validate_guarded_flags

def main():
    ap = argparse.ArgumentParser(prog="mise", description="Next-gen ETL (Stage runner)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run a stage")
    run.add_argument("stage", choices=["A"], help="Stage letter to run")
    run.add_argument("--in", dest="in_dir", default="data/ontology", help="Input ontology dir")
    run.add_argument("--build", dest="build_dir", default="etl2/build", help="Build root dir")
    run.add_argument("--verbose", action="store_true")

    args = ap.parse_args()

    if args.cmd == "run" and args.stage == "A":
        rc = run_stage_a(Path(args.in_dir), Path(args.build_dir), verbose=args.verbose)
        sys.exit(rc)

def run_stage_a(in_dir: Path, build_dir: Path, verbose: bool = False) -> int:
    """Stage A: Load + Lint + Normalize. Emits tmp artifacts + lint report."""
    tmp_dir = build_dir / "tmp"
    rpt_dir = build_dir / "report"
    ensure_dir(tmp_dir)
    ensure_dir(rpt_dir)

    lint = {"errors": [], "warnings": [], "stats": {}}

    # 1) Transforms canonicalization
    try:
        tdefs_canon, tstats = load_and_canonicalize_transforms(in_dir)
        write_json(tmp_dir / "transforms_canon.json", tdefs_canon)
        lint["stats"]["transforms"] = tstats
        if verbose:
            print(f"✓ transforms_canon.json written ({len(tdefs_canon)} families)")
    except Exception as e:
        lint["errors"].append(f"TRANSFORMS: {e}")

    # 2) Transform applicability normalization
    try:
        src = in_dir / "rules" / "transform_applicability.jsonl"
        if not src.exists():
            lint["warnings"].append(f"APPLICABILITY: missing {src}")
            norm_rows, n_stats = [], {"input": 0, "output": 0}
        else:
            from mise.stages.stage_a.schema_loader import read_jsonl
            rows = read_jsonl(src)
            norm_rows, n_stats = normalize_transform_applicability(rows)
            write_jsonl(tmp_dir / "transform_applicability.normalized.jsonl", norm_rows)
            if verbose:
                print(f"✓ transform_applicability.normalized.jsonl written ({len(norm_rows)} rows)")
        lint["stats"]["transform_applicability"] = n_stats
    except Exception as e:
        lint["errors"].append(f"APPLICABILITY: {e}")

    # 3) Guarded diet/safety rules validation
    try:
        rules_path = in_dir / "rules" / "diet_safety_rules.jsonl"
        if not rules_path.exists():
            lint["warnings"].append(f"FLAGS: missing {rules_path}")
            write_json(tmp_dir / "flags.rules.validated.json", {"count": 0, "ok": True})
        else:
            # parts + transforms needed for cross-ref
            from mise.stages.stage_a.schema_loader import read_json
            parts = read_json(in_dir / "parts.json")
            part_ids = [p["id"] for p in parts]
            # prefer canonical transforms we just wrote
            tdefs = tdefs_canon if 'tdefs_canon' in locals() else read_json(in_dir / "transforms.json")
            errors, meta = validate_guarded_flags(rules_path, tdefs, part_ids)
            lint["stats"]["flags"] = meta
            write_json(tmp_dir / "flags.rules.validated.json", {"count": meta["count"], "ok": len(errors) == 0})
            for msg in errors:
                lint["errors"].append(f"FLAGS: {msg}")
            if verbose:
                print(f"✓ flags.rules.validated.json written (rules={meta['count']})")
    except Exception as e:
        lint["errors"].append(f"FLAGS: {e}")

    # Finalize report
    write_json(rpt_dir / "lint.json", lint)

    # Exit code policy: any errors → non-zero
    if lint["errors"]:
        if verbose:
            print(json.dumps(lint, indent=2, ensure_ascii=False))
        print("✗ Stage A failed — see etl2/build/report/lint.json")
        return 1

    print("✓ Stage A completed cleanly")
    return 0

if __name__ == "__main__":
    main()
