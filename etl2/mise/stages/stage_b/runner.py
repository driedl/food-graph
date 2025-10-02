from __future__ import annotations
import shutil
from pathlib import Path
from mise.io import ensure_dir
from .substrates import build_substrates

def preflight(in_dir: Path, build_dir: Path) -> None:
    tcanon = build_dir / "tmp" / "transforms_canon.json"
    if not tcanon.exists():
        raise FileNotFoundError(f"missing {tcanon} — run Stage A first")
    compiled_taxa = build_dir / "compiled" / "taxa.jsonl"
    if not compiled_taxa.exists():
        raise FileNotFoundError(f"missing {compiled_taxa} — run Stage 0 first")

def run(in_dir: Path, build_dir: Path, verbose: bool = False) -> int:
    tmp_dir = build_dir / "tmp"
    graph_dir = build_dir / "graph"
    ensure_dir(tmp_dir); ensure_dir(graph_dir)
    build_substrates(in_dir=in_dir, tmp_dir=tmp_dir, graph_dir=graph_dir, verbose=verbose)
    print("✓ Stage B completed cleanly")
    return 0
