from __future__ import annotations
import json, shutil, subprocess, sys
from pathlib import Path
from typing import Dict, List, Tuple

def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for i, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("//"): continue
            yield i, json.loads(line)

def _collect_taxa(root: Path) -> List[Tuple[Path, int, dict]]:
    items: List[Tuple[Path, int, dict]] = []
    index = root / "index.jsonl"
    if index.exists():
        for ln, obj in _iter_jsonl(index): items.append((index, ln, obj))
    for f in sorted((root / "plantae" / "families").rglob("*.jsonl")):
        for ln, obj in _iter_jsonl(f): items.append((f, ln, obj))
    fungi = root / "fungi" / "fungi.jsonl"
    if fungi.exists():
        for ln, obj in _iter_jsonl(fungi): items.append((fungi, ln, obj))
    animals = root / "animalia" / "animals.jsonl"
    if animals.exists():
        for ln, obj in _iter_jsonl(animals): items.append((animals, ln, obj))
    return items

def _kingdom_key(id_: str) -> str:
    parts = id_.split(":")
    if len(parts) >= 2 and parts[0] == "tx": 
        if parts[1] in {"plantae", "fungi", "animalia"}:
            return parts[1]
    if id_ in {"tx:life", "tx:eukaryota"}: return "00_index"
    return "zz_other"

def _sort_key(obj: dict) -> tuple:
    id_ = obj["id"]
    if id_ == "tx:life": return (0, 0, 0, "")
    if id_ == "tx:eukaryota": return (0, 1, 0, "")
    group = _kingdom_key(id_)
    order = {"00_index": 0, "plantae": 1, "fungi": 2, "animalia": 3}.get(group, 9)
    # Add hierarchical depth (number of colons) to ensure parents come before children
    depth = len(id_.split(":")) - 1  # -1 because "tx:life" should be depth 0
    return (1, order, depth, id_)

def _normalize(obj: dict) -> dict:
    obj = dict(obj)
    obj.pop("tags", None)
    out = {
        "id": obj.pop("id"),
        "parent": obj.pop("parent", None),
        "rank": obj.pop("rank"),
        "display_name": obj.pop("display_name"),
        "latin_name": obj.pop("latin_name"),
    }
    if "aliases" in obj and isinstance(obj["aliases"], list):
        out["aliases"] = obj.pop("aliases")
    for k in sorted(obj.keys()):
        out[k] = obj[k]
    return out

def compile_taxa_into(*, taxa_root: Path, ontology_root: Path,
                      out_taxa_path: Path, compiled_dir: Path,
                      skip_validate: bool = False, verbose: bool = False) -> int:
    out_taxa_path.parent.mkdir(parents=True, exist_ok=True)

    # Optional validation (stage-local copy is recommended)
    if not skip_validate:
        val_script = (Path(__file__).parent / "validate_taxa.py")
        if val_script.exists():
            rc = subprocess.call([sys.executable, str(val_script), "--taxa-root", str(taxa_root)])
            if rc != 0:
                print("✗ Validation failed; aborting compile.", file=sys.stderr)
                return rc
        else:
            print("⚠️  validate_taxa.py not found; continuing", file=sys.stderr)

    dedup: Dict[str, Tuple[Path, int]] = {}
    objs: List[dict] = []
    for path, ln, obj in _collect_taxa(taxa_root):
        id_ = obj.get("id")
        if id_ in dedup:
            p2, ln2 = dedup[id_]
            print(f"ERROR: duplicate id during compile: {id_} at {path}:{ln} and {p2}:{ln2}", file=sys.stderr)
            return 1
        dedup[id_] = (path, ln)
        objs.append(_normalize(obj))

    objs.sort(key=_sort_key)
    with out_taxa_path.open("w", encoding="utf-8") as f:
        for o in objs:
            f.write(json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "\n")
    if verbose:
        print(f"✓ Wrote {len(objs)} taxa → {out_taxa_path}")

    # Copy assets into etl/build/compiled
    assets = ["attributes.json", "nutrients.json", "transforms.json", "categories.json"]
    for asset in assets:
        src = ontology_root / asset
        if src.exists():
            dst = compiled_dir / asset
            shutil.copy2(src, dst)
            if verbose: print(f"  ✓ Copied {asset}")
        else:
            print(f"  ⚠️  Missing asset: {src}")
    
    # Merge parts registry (core + derived)
    _merge_parts_registry(ontology_root, compiled_dir, verbose)
    # rules/ directory
    rules_src = ontology_root / "rules"
    rules_dst = compiled_dir / "rules"
    if rules_src.exists():
        if rules_dst.exists(): shutil.rmtree(rules_dst)
        shutil.copytree(rules_src, rules_dst)
        if verbose: print("  ✓ Copied rules/")

    return 0


def _merge_parts_registry(ontology_root: Path, compiled_dir: Path, verbose: bool) -> None:
    """Merge parts.core.json and parts.derived.jsonl into parts.registry.json"""
    import json
    
    # Load core parts
    core_parts = []
    core_path = ontology_root / "parts.json"
    if core_path.exists():
        with core_path.open("r", encoding="utf-8") as f:
            core_parts = json.load(f)
        if verbose: print(f"  ✓ Loaded {len(core_parts)} core parts")
    else:
        print(f"  ⚠️  Missing core parts: {core_path}")
    
    # Load derived parts
    derived_parts = []
    derived_path = ontology_root / "parts.derived.jsonl"
    if derived_path.exists():
        with derived_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("//"):
                    try:
                        derived_parts.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"  ⚠️  Invalid JSON in {derived_path}: {e}")
        if verbose: print(f"  ✓ Loaded {len(derived_parts)} derived parts")
    else:
        print(f"  ⚠️  Missing derived parts: {derived_path}")
    
    # Merge and validate
    all_parts = core_parts + derived_parts
    
    # Check for duplicate IDs
    seen_ids = set()
    for part in all_parts:
        part_id = part.get("id")
        if part_id in seen_ids:
            print(f"  ❌ Duplicate part ID: {part_id}")
            return
        seen_ids.add(part_id)
    
    # Write merged registry
    registry_path = compiled_dir / "parts.registry.json"
    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(all_parts, f, indent=2, ensure_ascii=False)
    
    if verbose: print(f"  ✓ Merged {len(all_parts)} parts → {registry_path}")
    
    # Also create parts.json for backward compatibility
    parts_path = compiled_dir / "parts.json"
    with parts_path.open("w", encoding="utf-8") as f:
        json.dump(all_parts, f, indent=2, ensure_ascii=False)
    
    if verbose: print(f"  ✓ Created parts.json for backward compatibility")
