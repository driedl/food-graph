#!/usr/bin/env python3
"""
compile_taxa.py

Compiles all validated shards into a single JSONL and copies required assets:
  data/ontology/compiled/taxa/taxa.jsonl
  data/ontology/compiled/attributes.json
  data/ontology/compiled/parts.json
  data/ontology/compiled/nutrients.json
  data/ontology/compiled/transforms.json

Steps:
- Optionally run a light, embedded validation (or invoke validate_taxa.py first in your ETL pipeline).
- Read index.jsonl, plantae family/genus shards, fungi.jsonl, animals.jsonl.
- Drop the 'tags' field if present (belt & suspenders).
- Enforce unique ids.
- Write objects in a stable order: index first (life, eukaryota, kingdoms), then Plantae, Fungi, Animalia by id.
- Copy all required asset files to compiled directory for db:build.
"""

from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Local lightweight JSONL reader (same behavior as in validate)
def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for i, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            yield i, json.loads(line)

def collect_taxa(root: Path) -> List[Tuple[Path, int, dict]]:
    items: List[Tuple[Path, int, dict]] = []

    index = root / "index.jsonl"
    if index.exists():
        for ln, obj in iter_jsonl(index):
            items.append((index, ln, obj))

    for f in sorted((root / "plantae" / "families").rglob("*.jsonl")):
        for ln, obj in iter_jsonl(f):
            items.append((f, ln, obj))

    fungi = root / "fungi" / "fungi.jsonl"
    if fungi.exists():
        for ln, obj in iter_jsonl(fungi):
            items.append((fungi, ln, obj))

    animals = root / "animalia" / "animals.jsonl"
    if animals.exists():
        for ln, obj in iter_jsonl(animals):
            items.append((animals, ln, obj))

    return items

def kingdom_key(id_: str) -> str:
    parts = id_.split(":")
    if len(parts) >= 3 and parts[0] == "tx":
        return parts[1]
    # index items: tx:life, tx:eukaryota
    if id_ in {"tx:life", "tx:eukaryota"}:
        return "00_index"
    return "zz_other"

def sort_key(obj: dict) -> tuple:
    """
    Order within compile:
      - index items first in domain order
      - then by kingdom group (plantae, fungi, animalia)
      - then by id lexicographically (stable)
    """
    id_ = obj["id"]
    if id_ == "tx:life":
        return (0, 0, "")
    if id_ == "tx:eukaryota":
        return (0, 1, "")
    rank = obj.get("rank", "")
    group = kingdom_key(id_)
    group_order = {"00_index": 0, "plantae": 1, "fungi": 2, "animalia": 3}
    return (1, group_order.get(group, 9), id_)

def normalize(obj: dict) -> dict:
    obj = dict(obj)  # shallow copy
    obj.pop("tags", None)  # ensure removed even if left behind
    # Normalize key order (purely aesthetic in output)
    ordered = {
        "id": obj.pop("id"),
        "parent": obj.pop("parent", None),
        "rank": obj.pop("rank"),
        "display_name": obj.pop("display_name"),
        "latin_name": obj.pop("latin_name"),
    }
    # Include aliases if present
    if "aliases" in obj and isinstance(obj["aliases"], list):
        ordered["aliases"] = obj.pop("aliases")
    # Append any remaining fields (e.g., notes) to not lose information
    for k in sorted(obj.keys()):
        ordered[k] = obj[k]
    return ordered

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taxa-root", default="data/ontology/taxa", help="Path to data/ontology/taxa/")
    ap.add_argument("--out", default="data/ontology/compiled/taxa.jsonl", help="Output JSONL file")
    ap.add_argument("--skip-validate", action="store_true", help="Skip calling validate_taxa.py before compiling")
    args = ap.parse_args()

    root = Path(args.taxa_root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not args.skip_validate:
        # Invoke validator first
        val_script = Path(__file__).parent / "validate_taxa.py"
        if not val_script.exists():
            print("WARNING: validate_taxa.py not found; continuing without pre-validation.", file=sys.stderr)
        else:
            rc = subprocess.call([sys.executable, str(val_script), "--taxa-root", str(root)])
            if rc != 0:
                print("✗ Validation failed; aborting compile.", file=sys.stderr)
                sys.exit(rc)

    dedup: Dict[str, Tuple[Path, int]] = {}
    objs: List[dict] = []

    for path, ln, obj in collect_taxa(root):
        id_ = obj.get("id")
        if id_ in dedup:
            p2, ln2 = dedup[id_]
            print(f"ERROR: duplicate id during compile: {id_} at {path}:{ln} and {p2}:{ln2}", file=sys.stderr)
            sys.exit(1)
        dedup[id_] = (path, ln)
        objs.append(normalize(obj))

    # Sort stable
    objs.sort(key=sort_key)

    with out.open("w", encoding="utf-8") as f:
        for o in objs:
            f.write(json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(f"✓ Wrote {len(objs)} taxa → {out}")
    
    # Copy required asset files for db:build
    print("📋 Copying required asset files...")
    asset_files = ["attributes.json", "parts.json", "nutrients.json", "transforms.json"]
    compiled_dir = out.parent.parent  # Go up one level from taxa/ to compiled/
    
    for asset in asset_files:
        src = root.parent / asset  # Go up one level from taxa/ to ontology/
        if src.exists():
            dst = compiled_dir / asset
            shutil.copy2(src, dst)
            print(f"  ✓ Copied {asset}")
        else:
            print(f"  ⚠️  Warning: {asset} not found at {src}")
    
    print(f"✓ All assets copied to {compiled_dir}")

if __name__ == "__main__":
    main()
