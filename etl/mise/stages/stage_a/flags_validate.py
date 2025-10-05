# -*- coding: utf-8 -*-
from __future__ import annotations
import json, re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from jsonschema import Draft202012Validator

# Minimal JSON Schema for guarded rules (kept local to avoid external deps files)
_GUARDED_RULE_SCHEMA: Dict[str, Any] = {
  "title": "Guarded Flag Rule",
  "type": "object",
  "required": ["flag_type", "emit", "when"],
  "additionalProperties": False,
  "properties": {
    "id": {"type": "string"},
    "flag_type": {"type": "string", "enum": ["safety", "dietary"]},
    "emit": {"type": "string"},
    "when": {
      "type": "object",
      "minProperties": 1,
      "additionalProperties": False,
      "properties": {
        "allOf": {"type": "array", "items": {"$ref": "#/$defs/cond"}},
        "anyOf": {"type": "array", "items": {"$ref": "#/$defs/cond"}},
        "noneOf": {"type": "array", "items": {"$ref": "#/$defs/cond"}}
      }
    },
    "notes": {"type": "string"}
  },
  "$defs": {
    "cond": {
      "oneOf": [
        {"$ref": "#/$defs/has_transform"},
        {"$ref": "#/$defs/has_part"},
        {"$ref": "#/$defs/param_cmp"}
      ]
    },
    "has_transform": {
      "type": "object", "additionalProperties": False,
      "required": ["has_transform"],
      "properties": {"has_transform": {"type": "string", "pattern": "^tf:[a-z0-9_]+$"}}
    },
    "has_part": {
      "type": "object", "additionalProperties": False,
      "required": ["has_part"],
      "properties": {"has_part": {"type": "string", "pattern": "^part:[a-z0-9_:]+$"}}
    },
    "param_cmp": {
      "type": "object", "additionalProperties": False,
      "required": ["param", "op"],
      "properties": {
        "param": {"type": "string", "pattern": "^tf:[a-z0-9_]+\\.[a-z0-9_.]+$"},
        "op": {"type": "string", "enum": ["exists","eq","ne","gt","gte","lt","lte","in","not_in"]},
        "value": {}
      },
      "allOf": [
        {"if": {"properties": {"op": {"const": "exists"}}}, "then": {"not": {"required": ["value"]}}},
        {"if": {"properties": {"op": {"enum": ["in","not_in"]}}}, "then": {"required": ["value"]}}
      ]
    }
  }
}

_PARAM_RE = re.compile(r"^(tf:[a-z0-9_]+)\.([a-z0-9_.]+)$")

def _index_transforms(tdefs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    # tdefs may be array or dict keyed by id
    if isinstance(tdefs, dict):
        return {k: v for k, v in tdefs.items()}
    return {t["id"]: t for t in tdefs}

def _param_exists(tdef: Dict[str, Any], param_path: str) -> bool:
    # We only guarantee first-segment check (e.g., cure.nitrite_ppm)
    first = param_path.split(".")[0]
    for p in (tdef.get("params") or []):
        if p.get("key") == first:
            return True
    return False

def _walk_conditions(group: List[Dict[str, Any]], t_idx: Dict[str, Any], part_ids: set, errs: List[str], loc: str) -> None:
    for cond in group:
        if "has_transform" in cond:
            tid = cond["has_transform"]
            if tid not in t_idx:
                errs.append(f"{loc}: unknown transform '{tid}'")
        elif "has_part" in cond:
            pid = cond["has_part"]
            if pid not in part_ids:
                errs.append(f"{loc}: unknown part '{pid}'")
        elif "param" in cond:
            m = _PARAM_RE.match(cond["param"])
            if not m:
                errs.append(f"{loc}: bad param path '{cond['param']}'")
            else:
                tid = m.group(1); ppath = m.group(2)
                tdef = t_idx.get(tid)
                if not tdef:
                    errs.append(f"{loc}: param references unknown transform '{tid}'")
                elif not _param_exists(tdef, ppath):
                    errs.append(f"{loc}: param '{ppath}' not in {tid}")

def validate_guarded_flags(rules_path: Path, tdefs: List[Dict[str, Any]] | Dict[str, Any], part_ids_list: List[str]) -> Tuple[List[str], Dict[str, int]]:
    """
    - JSON Schema validate each rule
    - Cross-ref: transforms and parts; param presence
    Returns (errors[], meta_stats)
    """
    errors: List[str] = []
    raw = []
    with rules_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("//"): continue
            try:
                raw.append(json.loads(line))
            except json.JSONDecodeError as e:
                errors.append(f"{rules_path}:{i}: invalid JSON: {e}")

    validator = Draft202012Validator(_GUARDED_RULE_SCHEMA)
    for idx, rec in enumerate(raw):
        for err in validator.iter_errors(rec):
            errors.append(f"{rules_path}[{idx}]: {err.message}")

    t_idx = _index_transforms(tdefs)
    part_ids = set(part_ids_list)

    for i, rule in enumerate(raw):
        loc = f"{rules_path}[{i}]"
        when = rule.get("when") or {}
        for key in ("allOf","anyOf","noneOf"):
            if key in when:
                _walk_conditions(when[key], t_idx, part_ids, errors, loc)

    return errors, {"count": len(raw)}
