from __future__ import annotations
from pathlib import Path
from rich.console import Console

from graph.io import ensure_dir
from .taxa_compile import compile_taxa_into
from .docs_compile import compile_docs_into

console = Console()

def run(in_dir: Path, build_dir: Path, skip_validate: bool = False, verbose: bool = False) -> int:
    compiled_dir = build_dir / "compiled"
    ensure_dir(compiled_dir)

    # 1) Compile taxa + copy assets into etl/build/compiled
    out_taxa = compiled_dir / "taxa.jsonl"
    rc = compile_taxa_into(
        taxa_root=in_dir / "taxa",
        ontology_root=in_dir,
        out_taxa_path=out_taxa,
        compiled_dir=compiled_dir,
        skip_validate=skip_validate,
        verbose=verbose,
    )
    if rc != 0:
        if verbose:
            console.print("  ❌ Taxa compilation failed", style="red")
        return rc

    # 2) Compile docs (disabled for now - MD files use old taxonomic hierarchy format)
    # out_docs = compiled_dir / "docs.jsonl"
    # rc = compile_docs_into(
    #     taxa_root=in_dir / "taxa",
    #     compiled_taxa_path=out_taxa,
    #     out_docs_path=out_docs,
    #     verbose=verbose,
    # )
    # if rc != 0:
    #     if verbose:
    #         console.print("  ❌ Docs compilation failed", style="red")
    #     return rc

    if verbose:
        # Count entries in output files for better feedback
        taxa_count = sum(1 for _ in out_taxa.open()) if out_taxa.exists() else 0
        console.print(f"  ✓ Compiled taxa ({taxa_count:,} entries)", style="green")
        console.print(f"  ✓ Docs compilation disabled (MD files use old taxonomic hierarchy)", style="yellow")
    
    return 0
