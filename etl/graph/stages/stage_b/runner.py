from __future__ import annotations
import shutil
from pathlib import Path
from rich.console import Console
from graph.io import ensure_dir
from .substrates import build_substrates

console = Console()

def preflight(in_dir: Path, build_dir: Path) -> None:
    tcanon = build_dir / "tmp" / "transforms_canon.json"
    if not tcanon.exists():
        raise FileNotFoundError(f"missing {tcanon} — run Stage A first")
    compiled_taxa = build_dir / "compiled" / "taxa.jsonl"
    if not compiled_taxa.exists():
        raise FileNotFoundError(f"missing {compiled_taxa} — run Stage 1 first")

def run(in_dir: Path, build_dir: Path, verbose: bool = False) -> int:
    tmp_dir = build_dir / "tmp"
    graph_dir = build_dir / "graph"
    ensure_dir(tmp_dir); ensure_dir(graph_dir)
    
    try:
        build_substrates(in_dir=in_dir, tmp_dir=tmp_dir, graph_dir=graph_dir, verbose=verbose)
        if verbose:
            # Count substrates for better feedback
            substrates_file = graph_dir / "substrates.jsonl"
            if substrates_file.exists():
                substrate_count = sum(1 for _ in substrates_file.open()) if substrates_file.exists() else 0
                console.print(f"  ✓ substrates.jsonl written ({substrate_count:,} entries)", style="green")
        return 0
    except Exception as e:
        if verbose:
            console.print(f"  ❌ Substrate building failed: {e}", style="red")
        return 1
