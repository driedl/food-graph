from __future__ import annotations
from pathlib import Path
from mise.io import ensure_dir
from .curated_seed import ingest_curated_tpt_seed

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
    ingest_curated_tpt_seed(in_dir=in_dir, tmp_dir=tmp_dir, verbose=verbose)
    print("✓ Stage C completed cleanly")
    return 0
