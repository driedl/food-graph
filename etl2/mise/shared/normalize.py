# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any, Tuple

def _strip_trailing_colon(s: str) -> str:
    return s[:-1] if isinstance(s, str) and s.endswith(":") else s

def _as_part_id(p: str) -> str:
    return p if p.startswith("part:") else f"part:{p}"

def normalize_applies_to(at) -> List[Dict[str, Any]]:
    """
    Accepts either strings (taxon_prefix) or objects {taxon_prefix, parts[]}.
    Normalizes to objects with normalized parts and trimmed prefixes.
    Dedupes by (taxon_prefix, tuple(parts)).
    """
    out: List[Dict[str, Any]] = []
    for item in (at or []):
        if isinstance(item, str):
            out.append({"taxon_prefix": _strip_trailing_colon(item), "parts": []})
        elif isinstance(item, dict):
            tp = _strip_trailing_colon(item.get("taxon_prefix", ""))
            parts = sorted({_as_part_id(p) for p in (item.get("parts") or [])})
            out.append({"taxon_prefix": tp, "parts": parts})
    uniq: Dict[Tuple[str, Tuple[str, ...]], Dict[str, Any]] = {}
    for row in out:
        key = (row["taxon_prefix"], tuple(row["parts"]))
        uniq[key] = row
    return list(uniq.values())
