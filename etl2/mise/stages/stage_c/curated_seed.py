from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import json

from ...io import read_json, read_jsonl, write_jsonl, ensure_dir

def ingest_curated_tpt_seed(
    in_dir: Path,   # ontology root
    tmp_dir: Path,  # build/tmp
    verbose: bool = False
):
    ensure_dir(tmp_dir)

    # Inputs
    derived = (in_dir / "rules" / "derived_foods.jsonl")
    if not derived.exists():
        write_jsonl(tmp_dir / "tpt_seed.jsonl", [])
        if verbose: print("• No derived_foods.jsonl found; seed is empty.")
        return

    # Substrates (from Stage B)
    subs = {(r["taxon_id"], r["part_id"]) for r in read_jsonl(tmp_dir.parent / "graph" / "substrates.jsonl")}
    # Transforms canon (Stage A)
    tcanon = read_json(tmp_dir / "transforms_canon.json")
    tf_defs = {t["id"]: t for t in tcanon}

    def is_identity(tid: str) -> bool:
        d = tf_defs.get(tid)
        return bool(d and d.get("identity"))

    def order_key(tid: str) -> int:
        d = tf_defs.get(tid)
        return int(d.get("order", 999)) if d else 999

    out: List[Dict[str, Any]] = []
    errors = 0

    for row in read_jsonl(derived):
        taxon_id = row.get("taxon_id"); part_id = row.get("part_id")
        if not taxon_id or not part_id:
            errors += 1; continue
        if (taxon_id, part_id) not in subs:
            # substrate missing → skip but count error
            errors += 1; continue

        path_full = row.get("transforms") or row.get("path") or []
        # keep only identity transforms, sorted by canonical order
        path_id = [s for s in path_full if s.get("id") in tf_defs and is_identity(s["id"])]
        path_id.sort(key=lambda s: order_key(s["id"]))

        out.append({
            "id": row.get("id"),  # optional human id (kept if present)
            "taxon_id": taxon_id,
            "part_id": part_id,
            "name": row.get("name"),
            "synonyms": row.get("synonyms", []),
            "family_hint": row.get("family") or row.get("family_id"),
            "path_full": path_full,   # original
            "path": path_id,          # identity-only canonical order
            "notes": row.get("notes")
        })

    write_jsonl(tmp_dir / "tpt_seed.jsonl", out)
    if verbose:
        print(f"• Curated TPT seed: accepted={len(out)}  skipped(errors)={errors}")
