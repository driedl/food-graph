from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple, Iterable, Optional
import json, hashlib

from graph.io import read_json, read_jsonl, write_jsonl, ensure_dir
from graph.io import write_json  # for lint report

def _index_transforms(tdefs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {t["id"]: t for t in tdefs if isinstance(t, dict) and "id" in t}

def _is_identity(tdef: Dict[str, Any]) -> bool:
    return bool(tdef.get("identity"))

def _identity_param_keys(tdef: Dict[str, Any]) -> List[str]:
    keys = []
    for p in tdef.get("params", []) or []:
        if isinstance(p, dict) and p.get("identity_param"):
            keys.append(p.get("key"))
    return keys

def _canon_path(steps: List[Dict[str, Any]], tindex: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    # keep only identity transforms, sort by canonical 'order'
    keep = []
    for s in steps or []:
        if not isinstance(s, dict):
            continue
        tid = s.get("id")
        td = tindex.get(tid)
        if not td:  # unknown transform → drop for safety
            continue
        if not _is_identity(td):
            continue
        keep.append({"id": tid, "params": s.get("params") or {}})
    # stable sort
    keep.sort(key=lambda s: int(tindex[s["id"]].get("order", 999)))
    return keep

def _params_map(raw: Any) -> Dict[str, Any]:
    """
    Normalize step.params into a {key: value} dict.
    Accepts:
      - dict: {"nitrite_ppm": 120}
      - array of {"key","value"}: [{"key":"nitrite_ppm","value":120}]
      - array of single-pair dicts: [{"nitrite_ppm":120}]
    Anything else → {}.
    """
    if isinstance(raw, dict):
        # keep only JSON-serializable scalars/objects as-is
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

def _identity_payload(steps: List[Dict[str, Any]], tindex: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for i, s in enumerate(steps):
        try:
            if not isinstance(s, dict):
                print(f"WARNING: step {i} is not a dict: {type(s)} - {s}")
                continue
            td = tindex.get(s["id"], {})
            id_keys = _identity_param_keys(td)
            pm = _params_map(s.get("params"))
            if id_keys:
                params = {k: pm.get(k) for k in sorted(id_keys) if k in pm}
            else:
                params = {}
            out.append({"id": s["id"], "params": params})
        except Exception as e:
            print(f"Error processing step {i}: {e}")
            print(f"Step: {s}")
            print(f"Step type: {type(s)}")
            raise
    return out

# ---- param bucketing ---------------------------------------------------------
def _load_param_buckets(rules_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Very small spec:
    {
      "tf:cure.nitrite_ppm": { "cuts": [0, 120], "labels": ["none","low","high"] }
    }
    Semantics: value <= cuts[i] → labels[i]; else → last label.
    """
    path = rules_dir / "param_buckets.json"
    if not path.exists():
        return {}
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
        return spec if isinstance(spec, dict) else {}
    except Exception:
        return {}

def _lint_param_buckets(buckets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate bucket specs:
      - cuts must be strictly non-decreasing numbers
      - len(labels) == len(cuts)+1
    """
    errors: List[str] = []
    warns: List[str] = []
    for key, cfg in (buckets or {}).items():
        try:
            if not isinstance(cfg, dict):
                errors.append(f"{key}: config must be a dict, got {type(cfg)}")
                continue
            cuts = cfg.get("cuts", [])
            labels = cfg.get("labels", [])
            if not isinstance(cuts, list) or not isinstance(labels, list):
                errors.append(f"{key}: cuts/labels must be arrays")
                continue
            # numeric + sorted (allow equal for <= semantics)
            try:
                fc = [float(c) for c in cuts]
            except Exception:
                errors.append(f"{key}: cuts contain non-numeric")
                continue
            if any(fc[i] > fc[i+1] for i in range(len(fc)-1)):
                errors.append(f"{key}: cuts must be non-decreasing")
            if len(labels) != len(cuts) + 1:
                errors.append(f"{key}: labels len must equal cuts len + 1")
        except Exception as e:
            errors.append(f"{key}: error processing config - {e}")
    return {"errors": errors, "warnings": warns, "ok": len(errors) == 0}

def _bucket_value(key: str, val: Any, buckets: Dict[str, Dict[str, Any]]) -> Any:
    cfg = buckets.get(key)
    if not cfg:
        return val
    cuts = cfg.get("cuts") or []
    labels = cfg.get("labels") or []
    if not isinstance(val, (int, float)) or not cuts or not labels:
        return val
    for i, cut in enumerate(cuts):
        try:
            if val <= float(cut):
                return labels[i] if i < len(labels) else val
        except Exception:
            return val
    return labels[-1] if labels else val

def _iter_sources(tmp_dir: Path) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Yield (source_tag, record) from known inputs in a deterministic order."""
    # Curated first (so it wins ties)
    seed = tmp_dir / "tpt_seed.jsonl"
    if seed.exists():
        for row in read_jsonl(seed):
            if not isinstance(row, dict):
                continue
            yield ("seed", row)
    gen = tmp_dir / "tpt_generated.jsonl"
    if gen.exists():
        for row in read_jsonl(gen):
            if not isinstance(row, dict):
                continue
            yield ("gen", row)

def _signature(taxon_id: str, part_id: str, id_payload: List[Dict[str, Any]]) -> str:
    """
    Canonical signature for dedupe, independent of ordering/pretty-print.
    Uses only identity-bearing content (ids + bucketed identity params).
    """
    blob = json.dumps(
        {"t": taxon_id, "p": part_id, "steps": id_payload},
        separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()

def _resolve_family_for_curated(taxon_id: str, part_id: str, path: List[Dict[str, Any]], 
                                family_rules: List[Dict[str, Any]]) -> Optional[str]:
    """
    Try to resolve a family for a curated TPT record based on its transform path and taxon/part.
    Returns the first matching family ID, or None if no match.
    """
    if not family_rules:
        return None
    
    # Convert path to transform IDs for matching
    path_tf_ids = [step["id"] for step in path if isinstance(step, dict) and "id" in step]
    
    for rule in family_rules:
        family_id = rule.get("family")
        applies_to = rule.get("applies_to", [])
        expected_path = rule.get("path", [])
        
        if not family_id or not expected_path:
            continue
            
        # Check if taxon/part matches any applicability rule
        taxon_matches = False
        part_matches = False
        
        for ap in applies_to:
            taxon_prefix = ap.get("taxon_prefix", "")
            parts = ap.get("parts", [])
            
            if not taxon_prefix or taxon_id.startswith(taxon_prefix):
                taxon_matches = True
            if not parts or part_id in parts:
                part_matches = True
                
            if taxon_matches and part_matches:
                break
        
        if not (taxon_matches and part_matches):
            continue
            
        # Check if transform path matches (allowing for optional transforms)
        expected_tf_ids = []
        for tf_def in expected_path:
            if isinstance(tf_def, dict) and "id" in tf_def:
                tf_id = tf_def["id"]
                if tf_id.endswith('?'):
                    # Optional transform - don't require it
                    continue
                expected_tf_ids.append(tf_id)
        
        # Check if all required transforms are present in the path
        if all(tf_id in path_tf_ids for tf_id in expected_tf_ids):
            return family_id
    
    return None

def _load_family_rules(in_dir: Path) -> List[Dict[str, Any]]:
    """Load family rules from families.json and family_allowlist.jsonl"""
    families_path = in_dir / "rules" / "families.json"
    allowlist_path = in_dir / "rules" / "family_allowlist.jsonl"
    
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
                # Optional transform - we'll handle this in matching
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

def _final_id(taxon_id: str, part_id: str, family: Optional[str], sig: str) -> str:
    # Keep this stable and short; last 12 of SHA1 is plenty for our scale
    suffix = sig[:12]
    return f"{taxon_id}|{part_id}|{suffix}"

def canon_and_id(in_dir: Path, tmp_dir: Path, verbose: bool = False) -> None:
    ensure_dir(tmp_dir)
    try:
        tcanon = read_json(tmp_dir / "transforms_canon.json")
        tindex = {}
        for i, t in enumerate(tcanon):
            if not isinstance(t, dict):
                continue
            if "id" not in t:
                continue
            tindex[t["id"]] = t
        
        buckets = _load_param_buckets(in_dir / "rules")
        
        # Load family rules for curated record resolution
        family_rules = _load_family_rules(in_dir)
        
        # write a lint report for buckets (best-effort)
        lint = _lint_param_buckets(buckets)
        try:
            write_json(tmp_dir / "param_buckets.lint.json", lint)
        except Exception:
            pass
    except Exception as e:
        if verbose:
            print(f"Error in setup phase: {e}")
        raise

    # 1) read + canonicalize + bucket → signature
    chosen: Dict[str, Dict[str, Any]] = {}   # sig -> row (prefer curated)
    source_of: Dict[str, str] = {}           # sig -> "seed" | "gen"

    for src, row in _iter_sources(tmp_dir):
        try:
            taxon_id = row["taxon_id"]; part_id = row["part_id"]
            family_hint = row.get("family_hint") or row.get("family")
            # Use identity-only, canon-ordered steps
            path_src = row.get("path") or []
            # normalize (sort by canonical order if present)
            def _ord(step): 
                if isinstance(step, dict) and "id" in step:
                    return int(tindex.get(step["id"], {}).get("order", 999))
                return 999
            path_canon = sorted([s for s in path_src if isinstance(s, dict) and s.get("id") in tindex and tindex[s["id"]].get("identity")], key=_ord)
            
            # identity payload + buckets (handles params as {} or [])
            id_payload = _identity_payload(path_canon, tindex)
            for step in id_payload:
                for k in list(step["params"].keys()):
                    pk = f'{step["id"]}.{k}'
                    step["params"][k] = _bucket_value(pk, step["params"][k], buckets)

            sig = _signature(taxon_id, part_id, id_payload)

            # Resolve family for curated records that don't have one
            resolved_family = family_hint
            if not resolved_family and src == "seed":
                resolved_family = _resolve_family_for_curated(taxon_id, part_id, path_canon, family_rules)
                if verbose and resolved_family:
                    print(f"• Resolved family '{resolved_family}' for curated record {taxon_id}:{part_id}")

            # prefer curated
            prev_src = source_of.get(sig)
            if prev_src == "seed":
                continue
            if prev_src == "gen" and src == "seed":
                # replace generated with curated
                pass
            source_of[sig] = src
            chosen[sig] = {
                "taxon_id": taxon_id,
                "part_id": part_id,
                "family_hint": resolved_family,
                "path": path_canon,
                "identity_payload": id_payload,
                "name": row.get("name"),
                "synonyms": row.get("synonyms", []),
                "notes": row.get("notes"),
            }
        except Exception as e:
            print(f"Error processing row from {src}: {e}")
            print(f"Row type: {type(row)}")
            print(f"Row keys: {list(row.keys()) if isinstance(row, dict) else 'not a dict'}")
            if "path" in row:
                print(f"Path type: {type(row['path'])}")
                print(f"Path content: {row['path']}")
            raise

    # 2) materialize IDs + write
    out_rows: List[Dict[str, Any]] = []
    # NOTE: kv = (signature, record)
    for sig, r in sorted(chosen.items(), key=lambda kv: (kv[1]["taxon_id"], kv[1]["part_id"], kv[0])):
        rid = _final_id(r["taxon_id"], r["part_id"], r.get("family_hint"), sig)
        out_rows.append({
            "id": rid,
            "taxon_id": r["taxon_id"],
            "part_id": r["part_id"],
            "family": r.get("family_hint") or "unknown",
            "path": r["path"],
            "identity": r["identity_payload"],
            "identity_hash": sig,
            "name": r.get("name"),
            "synonyms": r.get("synonyms", []),
            "notes": r.get("notes"),
        })

    write_jsonl(tmp_dir / "tpt_canon.jsonl", out_rows)
    if verbose:
        print(f"• Stage E: input(seen)={len(source_of)}  output(dedup)={len(out_rows)}")
