from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Any, Iterable, Tuple, Set
import json

from ...io import read_jsonl, write_jsonl, ensure_dir
from ...shared.normalize import normalize_applies_to

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


def _load_family_rules(path: Path) -> List[Dict[str, Any]]:
    """
    Spec (JSONL):
      {
        "family": "DRY_CURED_MEAT",
        "applies_to": ["tx:animalia", {"taxon_prefix":"tx:animalia:mammalia","parts":["part:meat"]}],
        "path": [{"id":"tf:cure","params":{"style":"dry"}}],
        "name": "optional name template input",
        "synonyms": ["optional", "syns"],
        "notes": "optional"
      }
    """
    if not path.exists():
        return []
    rows = read_jsonl(path)
    rules: List[Dict[str, Any]] = []
    for r in rows:
        fam = r.get("family")
        path = r.get("path") or []
        if not isinstance(fam, str) or not fam or not isinstance(path, list):
            continue
        def _params_map(raw: Any) -> Dict[str, Any]:
            if isinstance(raw, dict):
                return {str(k): v for k, v in raw.items()}
            if isinstance(raw, list):
                out: Dict[str, Any] = {}
                for item in raw:
                    if isinstance(item, dict):
                        if "key" in item and "value" in item:
                            out[str(item["key"])] = item["value"]
                        elif len(item) == 1:
                            k = next(iter(item.keys()))
                            out[str(k)] = item[k]
                return out
            return {}
        def _norm_path(path_arr: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            out = []
            for s in (path_arr or []):
                if isinstance(s, dict) and "id" in s:
                    out.append({"id": s["id"], "params": _params_map(s.get("params"))})
            return out
        rules.append({
            "family": fam,
            "applies_to": normalize_applies_to(r.get("applies_to") or []),
            "path": _norm_path(path),
            "name": r.get("name"),
            "synonyms": r.get("synonyms") or [],
            "notes": r.get("notes"),
        })
    return rules

def _substrate_pairs(graph_dir: Path) -> Set[Tuple[str, str]]:
    subs_path = graph_dir / "substrates.jsonl"
    if not subs_path.exists():
        return set()
    return {(r["taxon_id"], r["part_id"]) for r in read_jsonl(subs_path)}

def expand_families(
    in_dir: Path,    # ontology root (rules/*)
    tmp_dir: Path,   # build/tmp
    verbose: bool = False
) -> None:
    ensure_dir(tmp_dir)
    out_path  = tmp_dir / "tpt_generated.jsonl"

    # inputs
    rules_path = in_dir / "rules" / "family_expansions.jsonl"
    allowlist_path = in_dir / "rules" / "family_allowlist.jsonl"

    rules = _load_family_rules(rules_path)
    if not rules:
        # still emit empty file
        write_jsonl(out_path, [])
        if verbose:
            print("• Stage D: no family_expansions.jsonl → wrote empty generated set.")
        return

    allowed = _load_allowlist(allowlist_path)  # optional; empty set means "allow all"
    pairs = _substrate_pairs(tmp_dir.parent / "graph")

    out_rows: List[Dict[str, Any]] = []
    seen_keys: Set[Tuple[str, str, str, str]] = set()

    def _path_key(path: List[Dict[str, Any]]) -> str:
        # stable JSON for dedupe
        return json.dumps(path, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    for rule in rules:
        fam = rule["family"]
        if allowed and fam not in allowed:
            continue
        for ap in rule["applies_to"] or [{"taxon_prefix": "", "parts": []}]:
            tpref = ap.get("taxon_prefix", "")
            parts = ap.get("parts") or []
            # match substrate pairs
            for (t, p) in pairs:
                if not t.startswith(tpref):
                    continue
                if parts and p not in parts:
                    continue
                key = (t, p, fam, _path_key(rule["path"]))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                out_rows.append({
                    "taxon_id": t,
                    "part_id": p,
                    "family": fam,
                    "family_hint": fam,     # make Stage E family-aware
                    "path": rule["path"],
                    "name": rule.get("name"),
                    "synonyms": rule.get("synonyms") or [],
                    "notes": rule.get("notes"),
                })

    # determinism
    out_rows.sort(key=lambda r: (r["taxon_id"], r["part_id"], r["family"]))
    write_jsonl(out_path, out_rows)
    if verbose:
        print(f"• Stage D: generated {len(out_rows)} candidates from {len(rules)} rule(s).")
