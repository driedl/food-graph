from __future__ import annotations
from pathlib import Path

from ...io import ensure_dir
from .taxa_compile import compile_taxa_into
from .docs_compile import compile_docs_into

def run(in_dir: Path, build_dir: Path, skip_validate: bool = False, verbose: bool = False) -> int:
    compiled_dir = build_dir / "compiled"
    ensure_dir(compiled_dir)

    # 1) Compile taxa + copy assets into etl2/build/compiled
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
        print("✗ Stage 0 (taxa) failed")
        return rc

    # 2) Compile docs (uses compiled taxa we just wrote)
    out_docs = compiled_dir / "docs.jsonl"
    rc = compile_docs_into(
        taxa_root=in_dir / "taxa",
        compiled_taxa_path=out_taxa,
        out_docs_path=out_docs,
        verbose=verbose,
    )
    if rc != 0:
        print("✗ Stage 0 (docs) failed")
        return rc

    if verbose:
        print(f"✓ Stage 0 wrote: {out_taxa}")
        print(f"✓ Stage 0 wrote: {out_docs}")
    print("✓ Stage 0 completed cleanly")
    return 0
