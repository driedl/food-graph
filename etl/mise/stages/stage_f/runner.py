from __future__ import annotations
from pathlib import Path
from rich.console import Console
from mise.io import ensure_dir
from .sqlite_pack import build_sqlite

console = Console()

def preflight(in_dir: Path, build_dir: Path) -> None:
    req = [
        build_dir / "compiled" / "taxa.jsonl",
        build_dir / "compiled" / "parts.json",
        build_dir / "compiled" / "docs.jsonl",
        build_dir / "graph" / "substrates.jsonl",
        build_dir / "tmp" / "tp_index.jsonl",
        build_dir / "tmp" / "tpt_canon.jsonl",
        build_dir / "tmp" / "transforms_canon.json",
    ]
    missing = [str(p) for p in req if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing inputs for Stage F:\n  - " + "\n  - ".join(missing))

def run(in_dir: Path, build_dir: Path, verbose: bool = False) -> int:
    ensure_dir(build_dir / "database")
    try:
        # Use the configured database path (defaults to graph.dev.sqlite)
        from mise.config import BuildConfig
        config = BuildConfig.from_env()
        db_path = config.db_path
        # Fresh DB each run so schema/FTS updates apply deterministically
        if db_path.exists():
            db_path.unlink()
        build_sqlite(in_dir=in_dir, build_dir=build_dir, db_path=db_path, verbose=verbose)
        if verbose:
            console.print(f"  ✓ SQLite packed → {db_path}", style="green")
        return 0
    except Exception:
        if verbose:
            console.print_exception()
        return 1
