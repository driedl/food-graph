# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any, Tuple
from graph.shared.normalize import normalize_applies_to  # reuse

# normalize_applies_to now imported from shared module

def normalize_transform_applicability(recs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    - Normalizes 'applies_to' blocks (trailing colon, parts prefixing, dedupe)
    - Keeps 'transform' untouched except for strip
    - Fixes tofu edge: tf:press must apply to part:curd (not part:plant_milk)
    - Preserves exclude[] if present, with the same normalization
    Returns (normalized_rows, stats)
    """
    out: List[Dict[str, Any]] = []
    stats = {"input": len(recs), "output": 0, "press_fixes": 0}
    for rec in recs:
        tr = str(rec.get("transform", "")).strip()
        if not tr:
            # skip malformed rows silently; downstream lints will catch counts
            continue
        nr = {
            "transform": tr,
            "applies_to": normalize_applies_to(rec.get("applies_to") or []),
        }
        if rec.get("exclude"):
            nr["exclude"] = normalize_applies_to(rec.get("exclude") or [])

        # tofu fix: press must act on curd; never on plant_milk
        if tr == "tf:press":
            for row in nr["applies_to"]:
                parts = set(row.get("parts") or [])
                if "part:plant_milk" in parts:
                    parts.remove("part:plant_milk")
                    stats["press_fixes"] += 1
                if "part:curd" not in parts:
                    parts.add("part:curd")
                    stats["press_fixes"] += 1
                row["parts"] = sorted(parts)

        out.append(nr)
    stats["output"] = len(out)
    # stable order for determinism
    out.sort(key=lambda r: (r["transform"], json_key(r)))
    return out, stats

def json_key(obj: Dict[str, Any]) -> str:
    # lightweight stable ordering key
    tps = []
    for row in obj.get("applies_to", []):
        tps.append(f'{row.get("taxon_prefix","")}|{",".join(row.get("parts",[]))}')
    return ";".join(tps)
