from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple, Iterable, Optional
import json, hashlib

from ...io import read_json, read_jsonl, write_jsonl, ensure_dir

def _index_transforms(tdefs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {t["id"]: t for t in tdefs if isinstance(t, dict) and "id" in t}

def _is_identity(tdef: Dict[str, Any]) -> bool:
    return bool(tdef.get("identity"))

def _identity_param_keys(tdef: Dict[str, Any]) -> List[str]:
    keys = []
    for p in tdef.get("params", []) or []:
        if p.get("identity_param"):
            keys.append(p.get("key"))
    return keys

def _canon_path(steps: List[Dict[str, Any]], tindex: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    # keep only identity transforms, sort by canonical 'order'
    keep = []
    for s in steps or []:
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

def _identity_payload(steps: List[Dict[str, Any]], tindex: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for s in steps:
        td = tindex.get(s["id"], {})
        id_keys = _identity_param_keys(td)
        if id_keys:
            params = {k: s.get("params", {}).get(k) for k in sorted(id_keys) if k in (s.get("params") or {})}
        else:
            params = {}
        out.append({"id": s["id"], "params": params})
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
            yield ("seed", row)
    gen = tmp_dir / "tpt_generated.jsonl"
    if gen.exists():
        for row in read_jsonl(gen):
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

def _final_id(taxon_id: str, part_id: str, family: Optional[str], sig: str) -> str:
    # Keep this stable and short; last 12 of SHA1 is plenty for our scale
    suffix = sig[:12]
    fam = (family or "unknown")
    return f"tpt:{taxon_id}:{part_id}:{fam}:{suffix}"

def canon_and_id(in_dir: Path, tmp_dir: Path, verbose: bool = False) -> None:
    ensure_dir(tmp_dir)
    tcanon = read_json(tmp_dir / "transforms_canon.json")
    tindex = {t["id"]: t for t in tcanon}
    buckets = _load_param_buckets(in_dir / "rules")

    # 1) read + canonicalize + bucket → signature
    chosen: Dict[str, Dict[str, Any]] = {}   # sig -> row (prefer curated)
    source_of: Dict[str, str] = {}           # sig -> "seed" | "gen"

    for src, row in _iter_sources(tmp_dir):
        taxon_id = row["taxon_id"]; part_id = row["part_id"]
        # Use identity-only, canon-ordered steps
        path_src = row.get("path") or []
        # normalize (sort by canonical order if present)
        def _ord(step): return int(tindex.get(step["id"], {}).get("order", 999))
        path_canon = sorted([s for s in path_src if s.get("id") in tindex and tindex[s["id"]].get("identity")], key=_ord)

        # identity payload + buckets
        id_payload = _identity_payload(path_canon, tindex)
        for step in id_payload:
            for k in list(step["params"].keys()):
                pk = f'{step["id"]}.{k}'
                step["params"][k] = _bucket_value(pk, step["params"][k], buckets)

        sig = _signature(taxon_id, part_id, id_payload)

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
            "family_hint": row.get("family_hint"),
            "path": path_canon,
            "identity_payload": id_payload,
            "name": row.get("name"),
            "synonyms": row.get("synonyms", []),
            "notes": row.get("notes"),
        }

    # 2) materialize IDs + write
    out_rows: List[Dict[str, Any]] = []
    for sig, r in sorted(chosen.items(), key=lambda kv: (kv[1]["taxon_id"], kv[1]["part_id"], sig)):
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
