from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Any, Iterable, Tuple, Set
import json

from graph.io import read_jsonl, write_jsonl, read_json, ensure_dir
from graph.shared.normalize import normalize_applies_to

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


def _load_family_rules(families_path: Path, allowlist_path: Path) -> List[Dict[str, Any]]:
    """
    Load family definitions from families.json and applicability rules from family_allowlist.jsonl.
    Combine them to create expansion rules with proper (taxon, part) restrictions.
    """
    if not families_path.exists():
        return []
    
    # Load family definitions
    families = read_json(families_path)
    if not isinstance(families, list):
        families = [families] if isinstance(families, dict) else []
    
    # Load allowlist rules
    allowlist_rules = []
    if allowlist_path.exists():
        allowlist_data = read_jsonl(allowlist_path)
        # Group by family
        allowlist_by_family = {}
        for rule in allowlist_data:
            fam_id = rule.get("family")
            if fam_id:
                if fam_id not in allowlist_by_family:
                    allowlist_by_family[fam_id] = []
                allowlist_by_family[fam_id].append({
                    "taxon_prefix": rule.get("taxon_prefix", ""),
                    "parts": rule.get("parts", [])
                })
    else:
        allowlist_by_family = {}
    
    rules: List[Dict[str, Any]] = []
    for family in families:
        fam_id = family.get("id")
        identity_transforms = family.get("identity_transforms", [])
        
        if not fam_id or not identity_transforms:
            continue
            
        # Convert identity_transforms to path format
        path = []
        for tf_id in identity_transforms:
            if tf_id.endswith('?'):
                # Optional transform - we'll handle this in expansion
                tf_id = tf_id[:-1]
            path.append({"id": tf_id, "params": {}})
        
        # Get applicability rules for this family
        applies_to = allowlist_by_family.get(fam_id, [])
        if not applies_to:
            # If no allowlist rules, apply to all substrates (fallback)
            applies_to = [{"taxon_prefix": "", "parts": []}]
        
        # Create expansion rule for this family
        rules.append({
            "family": fam_id,
            "applies_to": applies_to,
            "path": path,
            "name": family.get("display_name", fam_id),
            "synonyms": [],
            "notes": f"Generated from families.json + allowlist for {fam_id}"
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
    families_path = in_dir / "rules" / "families.json"
    allowlist_path = in_dir / "rules" / "family_allowlist.jsonl"

    rules = _load_family_rules(families_path, allowlist_path)
    if not rules:
        # still emit empty file
        write_jsonl(out_path, [])
        if verbose:
            print("• Stage D: no families.json → wrote empty generated set.")
        return
    pairs = _substrate_pairs(tmp_dir.parent / "graph")

    out_rows: List[Dict[str, Any]] = []
    seen_keys: Set[Tuple[str, str, str, str]] = set()

    def _path_key(path: List[Dict[str, Any]]) -> str:
        # stable JSON for dedupe
        return json.dumps(path, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    for rule in rules:
        fam = rule["family"]
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
