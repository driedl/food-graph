#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
from rich.console import Console
from rich.text import Text

from mise.stages.stage_0.runner import run as run_0
from mise.stages.stage_a.runner import run as run_A
from mise.stages.stage_b.runner import run as run_B, preflight as pre_B
from mise.stages.stage_c.runner import run as run_C, preflight as pre_C

console = Console()

def print_stage_header(stage_id: str, description: str):
    """Print a colored stage header"""
    text = Text(f"🔄 Stage {stage_id}: {description}...", style="blue bold")
    console.print(text)

def print_success(message: str, duration_ms: float = None):
    """Print a success message with optional timing"""
    if duration_ms is not None:
        text = Text(f"  ✓ {message} in {duration_ms:.0f}ms", style="green")
    else:
        text = Text(f"  ✓ {message}", style="green")
    console.print(text)

def print_error(message: str):
    """Print an error message"""
    text = Text(f"  ❌ {message}", style="red bold")
    console.print(text)

def print_warning(message: str):
    """Print a warning message"""
    text = Text(f"  ⚠️ {message}", style="yellow")
    console.print(text)

def print_stage_complete(stage_id: str, duration_ms: float):
    """Print stage completion with timing"""
    text = Text(f"✅ Stage {stage_id} completed in {duration_ms:.0f}ms", style="green bold")
    console.print(text)

def print_pipeline_complete(total_ms: float):
    """Print pipeline completion with total timing"""
    text = Text(f"🎉 Pipeline completed successfully in {total_ms:.2f}s", style="green bold")
    console.print(text)

def run_stage_with_timing(stage_func, stage_id: str, description: str, *args, **kwargs):
    """Run a stage function with timing and colored output"""
    print_stage_header(stage_id, description)
    start_time = time.time()
    
    try:
        rc = stage_func(*args, **kwargs)
        duration_ms = (time.time() - start_time) * 1000
        
        if rc == 0:
            print_stage_complete(stage_id, duration_ms)
        else:
            print_error(f"Stage {stage_id} failed with exit code {rc}")
        
        return rc, duration_ms
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        print_error(f"Stage {stage_id} failed: {e}")
        return 1, duration_ms

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
        total_start = time.time()
        
        if args.stage == "0":
            rc, _ = run_stage_with_timing(run_0, "0", "Compiling taxa and docs", in_dir, build_dir, False, args.verbose)
            sys.exit(rc)
        if args.stage == "A":
            rc, _ = run_stage_with_timing(run_A, "A", "Normalizing transforms and rules", in_dir, build_dir, args.verbose)
            sys.exit(rc)
        if args.stage == "B":
            try: 
                pre_B(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight B: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_timing(run_B, "B", "Building substrates", in_dir, build_dir, args.verbose)
            sys.exit(rc)
        if args.stage == "C":
            try: 
                pre_C(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight C: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_timing(run_C, "C", "Ingesting curated seed", in_dir, build_dir, args.verbose)
            sys.exit(rc)
        if args.stage in ("0ABC", "build"):
            # Run all stages with timing
            rc, _ = run_stage_with_timing(run_0, "0", "Compiling taxa and docs", in_dir, build_dir, False, args.verbose)
            if rc != 0: sys.exit(rc)
            
            rc, _ = run_stage_with_timing(run_A, "A", "Normalizing transforms and rules", in_dir, build_dir, args.verbose)
            if rc != 0: sys.exit(rc)
            
            try: 
                pre_B(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight B: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_timing(run_B, "B", "Building substrates", in_dir, build_dir, args.verbose)
            if rc != 0: sys.exit(rc)
            
            try: 
                pre_C(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight C: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_timing(run_C, "C", "Ingesting curated seed", in_dir, build_dir, args.verbose)
            
            total_duration = (time.time() - total_start) * 1000
            if rc == 0:
                print_pipeline_complete(total_duration / 1000)
            sys.exit(rc)
            
        if args.stage == "0A":
            rc, _ = run_stage_with_timing(run_0, "0", "Compiling taxa and docs", in_dir, build_dir, False, args.verbose)
            if rc != 0: sys.exit(rc)
            rc, _ = run_stage_with_timing(run_A, "A", "Normalizing transforms and rules", in_dir, build_dir, args.verbose)
            sys.exit(rc)
            
        if args.stage == "0AB":
            rc, _ = run_stage_with_timing(run_0, "0", "Compiling taxa and docs", in_dir, build_dir, False, args.verbose)
            if rc != 0: sys.exit(rc)
            
            rc, _ = run_stage_with_timing(run_A, "A", "Normalizing transforms and rules", in_dir, build_dir, args.verbose)
            if rc != 0: sys.exit(rc)
            
            try: 
                pre_B(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight B: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_timing(run_B, "B", "Building substrates", in_dir, build_dir, args.verbose)
            sys.exit(rc)

if __name__ == "__main__":
    main()
