from __future__ import annotations
from pathlib import Path
from rich.console import Console
from mise.io import ensure_dir
from .curated_seed import ingest_curated_tpt_seed

console = Console()

def preflight(in_dir: Path, build_dir: Path) -> None:
    subs = build_dir / "graph" / "substrates.jsonl"
    if not subs.exists():
        raise FileNotFoundError(f"missing {subs} — run Stage B first")
    tcanon = build_dir / "tmp" / "transforms_canon.json"
    if not tcanon.exists():
        raise FileNotFoundError(f"missing {tcanon} — run Stage A first")

def run(in_dir: Path, build_dir: Path, verbose: bool = False) -> int:
    tmp_dir = build_dir / "tmp"
    ensure_dir(tmp_dir)
    
    try:
        ingest_curated_tpt_seed(in_dir=in_dir, tmp_dir=tmp_dir, verbose=verbose)
        if verbose:
            # Count curated seed entries for better feedback
            curated_file = tmp_dir / "tpt_seed.jsonl"
            if curated_file.exists():
                curated_count = sum(1 for _ in curated_file.open()) if curated_file.exists() else 0
                console.print(f"  ✓ tpt_seed.jsonl written ({curated_count:,} entries)", style="green")
        return 0
    except Exception as e:
        if verbose:
            console.print(f"  ❌ Curated seed ingestion failed: {e}", style="red")
        return 1
