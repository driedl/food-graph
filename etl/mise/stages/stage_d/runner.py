from __future__ import annotations
from pathlib import Path
from rich.console import Console
from mise.io import ensure_dir
from .family_expand import expand_families

console = Console()

def preflight(in_dir: Path, build_dir: Path) -> None:
    seed = build_dir / "tmp" / "tpt_seed.jsonl"
    if not seed.exists():
        # Allow empty expansions; Stage C may have produced empty seed
        console.print("  ⚠️  Stage C seed missing; Stage D will emit empty output.", style="yellow")

def run(in_dir: Path, build_dir: Path, verbose: bool = False) -> int:
    tmp_dir = build_dir / "tmp"
    ensure_dir(tmp_dir)
    try:
        expand_families(in_dir=in_dir, tmp_dir=tmp_dir, verbose=verbose)
        if verbose:
            out = tmp_dir / "tpt_generated.jsonl"
            cnt = sum(1 for _ in out.open()) if out.exists() else 0
            console.print(f"  ✓ tpt_generated.jsonl written ({cnt:,} entries)", style="green")
        return 0
    except Exception as e:
        if verbose:
            console.print(f"  ❌ Family expansion failed: {e}", style="red")
        return 1
