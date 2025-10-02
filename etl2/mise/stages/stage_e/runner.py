from __future__ import annotations
from pathlib import Path
from rich.console import Console
from mise.io import ensure_dir
from .canon_ids import canon_and_id

console = Console()

def preflight(in_dir: Path, build_dir: Path) -> None:
    tcanon = build_dir / "tmp" / "transforms_canon.json"
    if not tcanon.exists():
        raise FileNotFoundError(f"missing {tcanon} — run Stage A first")
    # Allow empty sources; we still emit an empty file

def run(in_dir: Path, build_dir: Path, verbose: bool = False) -> int:
    tmp_dir = build_dir / "tmp"
    ensure_dir(tmp_dir)
    try:
        canon_and_id(in_dir=in_dir, tmp_dir=tmp_dir, verbose=verbose)
        if verbose:
            out = tmp_dir / "tpt_canon.jsonl"
            cnt = sum(1 for _ in out.open()) if out.exists() else 0
            console.print(f"  ✓ tpt_canon.jsonl written ({cnt:,} entries)", style="green")
        return 0
    except Exception as e:
        if verbose:
            console.print(f"  ❌ Canonicalization failed: {e}", style="red")
        return 1
