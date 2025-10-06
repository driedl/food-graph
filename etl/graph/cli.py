#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
from rich.console import Console
from rich.text import Text

from graph.stages.stage_0.runner import run as run_0
from graph.stages.stage_a.runner import run as run_A
from graph.stages.stage_b.runner import run as run_B, preflight as pre_B
from graph.stages.stage_c.runner import run as run_C, preflight as pre_C
from graph.stages.stage_d.runner import run as run_D, preflight as pre_D
from graph.stages.stage_e.runner import run as run_E, preflight as pre_E
from graph.stages.stage_f.runner import run as run_F, preflight as pre_F
from graph.contracts.engine import verify

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

def run_stage_with_tests(stage_func, stage_id: str, description: str, in_dir: Path, build_dir: Path, verbose: bool, with_tests: bool, *args, **kwargs):
    """Run a stage function with timing, colored output, and optional contract verification"""
    print_stage_header(stage_id, description)
    start_time = time.time()
    
    try:
        rc = stage_func(*args, **kwargs)
        duration_ms = (time.time() - start_time) * 1000
        
        if rc == 0:
            print_stage_complete(stage_id, duration_ms)
            
            # Run contract verification if requested
            if with_tests:
                verify_start = time.time()
                verify_rc = verify(f"stage_{stage_id.lower()}", in_dir, build_dir, verbose)
                verify_duration = (time.time() - verify_start) * 1000
                
                if verify_rc == 0:
                    console.print(f"  ✓ Contract verification passed in {verify_duration:.0f}ms", style="green")
                else:
                    console.print(f"  ❌ Contract verification failed in {verify_duration:.0f}ms", style="red")
                    return 1, duration_ms
        else:
            print_error(f"Stage {stage_id} failed with exit code {rc}")
        
        return rc, duration_ms
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        print_error(f"Stage {stage_id} failed: {e}")
        return 1, duration_ms

def main():
    ap = argparse.ArgumentParser(prog="graph", description="Next-gen ETL (Stage runner)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run a stage")
    run.add_argument("stage", choices=["0", "A", "B", "C", "D", "E", "F", "0A", "0AB", "0ABC", "0ABCDE", "0ABCDEF", "build"], help="Stage(s) to run")
    run.add_argument("--in", dest="in_dir", default="data/ontology")
    run.add_argument("--build", dest="build_dir", default="etl/build")
    run.add_argument("--verbose", action="store_true")
    run.add_argument("--with-tests", action="store_true", help="Run contract verification after each stage")
    
    test = sub.add_parser("test", help="Test a stage's contract")
    test.add_argument("stage", choices=["0", "A", "B", "C", "D", "E", "F"], help="Stage to test")
    test.add_argument("--in", dest="in_dir", default="data/ontology")
    test.add_argument("--build", dest="build_dir", default="etl/build")
    test.add_argument("--verbose", action="store_true")
    
    args = ap.parse_args()

    if args.cmd == "run":
        in_dir = Path(args.in_dir); build_dir = Path(args.build_dir)
        total_start = time.time()
        
        if args.stage == "0":
            rc, _ = run_stage_with_tests(run_0, "0", "Compiling taxa and docs", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, False, args.verbose)
            sys.exit(rc)
        if args.stage == "A":
            rc, _ = run_stage_with_tests(run_A, "A", "Normalizing transforms and rules", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            sys.exit(rc)
        if args.stage == "B":
            try: 
                pre_B(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight B: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_tests(run_B, "B", "Building substrates", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            sys.exit(rc)
        if args.stage == "C":
            try: 
                pre_C(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight C: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_tests(run_C, "C", "Ingesting curated seed", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            sys.exit(rc)
        if args.stage == "D":
            try: 
                pre_D(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight D: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_tests(run_D, "D", "Family expansions", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            sys.exit(rc)
        if args.stage == "E":
            try: 
                pre_E(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight E: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_tests(run_E, "E", "Canonicalization & IDs", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            sys.exit(rc)
        if args.stage == "F":
            try: 
                pre_F(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight F: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_tests(run_F, "F", "SQLite graph packer", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            sys.exit(rc)
        if args.stage in ("0ABC", "0ABCDE", "0ABCDEF", "build"):
            # Run all stages with timing and optional tests
            rc, _ = run_stage_with_tests(run_0, "0", "Compiling taxa and docs", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, False, args.verbose)
            if rc != 0: sys.exit(rc)
            
            rc, _ = run_stage_with_tests(run_A, "A", "Normalizing transforms and rules", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            if rc != 0: sys.exit(rc)
            
            try: 
                pre_B(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight B: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_tests(run_B, "B", "Building substrates", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            if rc != 0: sys.exit(rc)
            
            try: 
                pre_C(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight C: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_tests(run_C, "C", "Ingesting curated seed", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            if rc != 0: sys.exit(rc)
            
            try: 
                pre_D(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight D: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_tests(run_D, "D", "Family expansions", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            if rc != 0: sys.exit(rc)
            
            try: 
                pre_E(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight E: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_tests(run_E, "E", "Canonicalization & IDs", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            if rc != 0: sys.exit(rc)
            
            try: 
                pre_F(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight F: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_tests(run_F, "F", "SQLite graph packer", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            
            total_duration = (time.time() - total_start) * 1000
            if rc == 0:
                print_pipeline_complete(total_duration / 1000)
            sys.exit(rc)
            
        if args.stage == "0A":
            rc, _ = run_stage_with_tests(run_0, "0", "Compiling taxa and docs", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, False, args.verbose)
            if rc != 0: sys.exit(rc)
            rc, _ = run_stage_with_tests(run_A, "A", "Normalizing transforms and rules", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            sys.exit(rc)
            
        if args.stage == "0AB":
            rc, _ = run_stage_with_tests(run_0, "0", "Compiling taxa and docs", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, False, args.verbose)
            if rc != 0: sys.exit(rc)
            
            rc, _ = run_stage_with_tests(run_A, "A", "Normalizing transforms and rules", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            if rc != 0: sys.exit(rc)
            
            try: 
                pre_B(in_dir, build_dir)
            except Exception as e: 
                print_error(f"Preflight B: {e}")
                sys.exit(2)
            rc, _ = run_stage_with_tests(run_B, "B", "Building substrates", in_dir, build_dir, args.verbose, args.with_tests, in_dir, build_dir, args.verbose)
            sys.exit(rc)
    
    elif args.cmd == "test":
        in_dir = Path(args.in_dir); build_dir = Path(args.build_dir)
        stage_map = {"0": "stage_0", "A": "stage_a", "B": "stage_b", "C": "stage_c", "D": "stage_d", "E": "stage_e", "F": "stage_f"}
        stage_name = stage_map[args.stage]
        
        print_stage_header(f"Test {args.stage}", f"Contract verification")
        rc = verify(stage_name, in_dir, build_dir, args.verbose)
        sys.exit(rc)

if __name__ == "__main__":
    main()
