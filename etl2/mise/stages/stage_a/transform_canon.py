# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from pathlib import Path
from copy import deepcopy
from mise.stages.stage_a.schema_loader import read_json

# Built-in opinionated overrides to ensure stable identity semantics & params
_BUILTIN_OVERRIDES: Dict[str, Dict[str, Any]] = {
  "tf:smoke": {
    "identity": True,
    "class": "identity",
    "order": 70,
    "params": [
      {"key": "mode", "kind": "enum", "enum": ["cold","hot"], "identity_param": True},
      {"key": "time_h", "kind": "number", "identity_param": False},
      {"key": "temp_C", "kind": "number", "identity_param": False},
    ],
    "notes": "Canonicalize to mode=cold|hot; temp/time process params."
  },
  "tf:cure": {
    "identity": True,
    "class": "identity",
    "order": 60,
    "params": [
      {"key": "style", "kind": "enum", "enum": ["dry","wet"], "identity_param": True},
      {"key": "nitrite_ppm", "kind": "number", "identity_param": True},
      {"key": "salt_pct", "kind": "number", "identity_param": False},
    ],
    "notes": "style + nitrite_ppm are identity-bearing."
  },
  "tf:refine_oil": {
    "identity": True,
    "class": "identity",
    "order": 90,
    "params": [
      {"key": "steps", "kind": "enum", "enum": ["degum","neutralize","bleach","deodorize"], "identity_param": False}
    ],
    "notes": "Refined vs virgin split."
  },
  "tf:salt": {
    "identity": True,
    "class": "identity",
    "order": 55,
    "params": [
      {"key": "salt_pct", "kind": "number", "identity_param": True},
      {"key": "method", "kind": "enum", "enum": ["dry","brine"], "identity_param": False},
    ],
    "notes": "salt_pct drives BRINED_FERMENT_VEG bucketing."
  },
  "tf:clarify": {
    "identity": True,
    "class": "identity",
    "order": 95,
    "params": [],
    "notes": "Butter → ghee/brown butter archetypes."
  },
}

def _dict_by_id(arr: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {d["id"]: d for d in arr}

def _merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow merge + param array replacement if provided in b."""
    out = deepcopy(a)
    for k, v in b.items():
        if k == "params" and isinstance(v, list):
            out["params"] = deepcopy(v)
        else:
            out[k] = deepcopy(v)
    return out

def _apply_alignment_fixes(td: Dict[str, Any]) -> Dict[str, Any]:
    """Tolerate older param naming by mapping to canonical keys in-schema only."""
    # If a transforms.json already uses 'style' for smoke, map to mode in SCHEMA
    if td["id"] == "tf:smoke":
        # ensure 'mode' exists in schema — users may still pass 'style'; input canonicalization is later
        pass
    # Additional soft fixes could go here
    return td

def load_and_canonicalize_transforms(ontology_dir: Path) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Loads data/ontology/transforms.json (+ optional rules/transform_overrides.json)
    Applies built-in overrides to guarantee identity-bearing semantics for key families.
    Emits a canonical, deterministic array of transform defs, sorted by id.
    """
    base = read_json(ontology_dir / "transforms.json")
    if not isinstance(base, list):
        raise ValueError("transforms.json must be an array of objects")

    # optional external overrides file
    overrides_path = ontology_dir / "rules" / "transform_overrides.json"
    overrides = {}
    if overrides_path.exists():
        raw = read_json(overrides_path)
        if isinstance(raw, list):
            overrides = _dict_by_id(raw)
        elif isinstance(raw, dict):
            overrides = raw
        else:
            raise ValueError("transform_overrides.json must be array or map keyed by id")

    base_map = _dict_by_id(base)
    # merge precedence: base → external overrides → builtin overrides
    merged: Dict[str, Dict[str, Any]] = {}
    for tid, tdef in base_map.items():
        out = deepcopy(tdef)
        if tid in overrides:
            out = _merge(out, overrides[tid])
        if tid in _BUILTIN_OVERRIDES:
            out = _merge(out, _BUILTIN_OVERRIDES[tid])
        out.setdefault("identity", False)
        out.setdefault("order", 999)
        # params array always present
        out["params"] = list(out.get("params") or [])
        out = _apply_alignment_fixes(out)
        merged[tid] = out

    # stable deterministic list
    result = [merged[k] for k in sorted(merged.keys())]
    stats = {"input": len(base), "overridden_external": len(overrides), "overridden_builtin": len(_BUILTIN_OVERRIDES), "output": len(result)}
    return result, stats
