#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path

from mise.stages.stage_0.runner import run as run_0
from mise.stages.stage_a.runner import run as run_A
from mise.stages.stage_b.runner import run as run_B, preflight as pre_B
from mise.stages.stage_c.runner import run as run_C, preflight as pre_C

def main():
    ap = argparse.ArgumentParser(prog="mise", description="Next-gen ETL (Stage runner)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run a stage")
    run.add_argument("stage", choices=["0", "A", "B", "C", "0A", "0AB", "0ABC", "build"], help="Stage(s) to run")
    run.add_argument("--in", dest="in_dir", default="data/ontology")
    run.add_argument("--build", dest="build_dir", default="etl2/build")
    run.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.cmd == "run":
        in_dir = Path(args.in_dir); build_dir = Path(args.build_dir)
        if args.stage == "0":
            sys.exit(run_0(in_dir, build_dir, skip_validate=False, verbose=args.verbose))
        if args.stage == "A":
            sys.exit(run_A(in_dir, build_dir, verbose=args.verbose))
        if args.stage == "B":
            try: pre_B(in_dir, build_dir)
            except Exception as e: print(f"✗ Preflight B: {e}"); sys.exit(2)
            sys.exit(run_B(in_dir, build_dir, verbose=args.verbose))
        if args.stage == "C":
            try: pre_C(in_dir, build_dir)
            except Exception as e: print(f"✗ Preflight C: {e}"); sys.exit(2)
            sys.exit(run_C(in_dir, build_dir, verbose=args.verbose))
        if args.stage in ("0ABC", "build"):
            rc = run_0(in_dir, build_dir, skip_validate=False, verbose=args.verbose)
            if rc != 0: sys.exit(rc)
            rc = run_A(in_dir, build_dir, verbose=args.verbose)
            if rc != 0: sys.exit(rc)
            try: pre_B(in_dir, build_dir)
            except Exception as e: print(f"✗ Preflight B: {e}"); sys.exit(2)
            rc = run_B(in_dir, build_dir, verbose=args.verbose)
            if rc != 0: sys.exit(rc)
            try: pre_C(in_dir, build_dir)
            except Exception as e: print(f"✗ Preflight C: {e}"); sys.exit(2)
            rc = run_C(in_dir, build_dir, verbose=args.verbose)
            sys.exit(rc)
        if args.stage == "0A":
            rc = run_0(in_dir, build_dir, skip_validate=False, verbose=args.verbose)
            if rc != 0: sys.exit(rc)
            sys.exit(run_A(in_dir, build_dir, verbose=args.verbose))
        if args.stage == "0AB":
            rc = run_0(in_dir, build_dir, skip_validate=False, verbose=args.verbose)
            if rc != 0: sys.exit(rc)
            rc = run_A(in_dir, build_dir, verbose=args.verbose)
            if rc != 0: sys.exit(rc)
            try: pre_B(in_dir, build_dir)
            except Exception as e: print(f"✗ Preflight B: {e}"); sys.exit(2)
            sys.exit(run_B(in_dir, build_dir, verbose=args.verbose))

if __name__ == "__main__":
    main()
