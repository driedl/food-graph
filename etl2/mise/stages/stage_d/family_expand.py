from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Any
import json

from ...io import read_jsonl, write_jsonl, ensure_dir

def _load_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    rows = read_jsonl(path)
    out = set()
    for r in rows:
        fam = r.get("family")
        if isinstance(fam, str) and fam:
            out.add(fam)
    return out

def _load_families_map(path: Path) -> Dict[str, Dict[str, Any]]:
    # Optional, format is up to you; we only pass-through currently
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def expand_families(
    in_dir: Path,    # ontology root (rules/families.json, rules/family_allowlist.jsonl)
    tmp_dir: Path,   # build/tmp
    verbose: bool = False
) -> None:
    ensure_dir(tmp_dir)
    seed_path = tmp_dir / "tpt_seed.jsonl"
    out_path  = tmp_dir / "tpt_generated.jsonl"
    
    # Stage D should NOT pass through curated items - that causes duplicates in Stage E
    # Instead, Stage D should only generate NEW items based on family expansions
    # For now, emit empty file since we don't have family expansion logic yet
    write_jsonl(out_path, [])
    if verbose:
        print("• Stage D: No family expansions implemented yet; generated file empty.")
