from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple, Iterable, Set, Any
import json

from ...io import read_json, read_jsonl, write_jsonl, ensure_dir
from ...shared.normalize import normalize_applies_to

# --- helpers -----------------------------------------------------------------

def _strip_colon(s: str) -> str:
    return s[:-1] if s.endswith(":") else s

def _as_part_id(p: str) -> str:
    return p if p.startswith("part:") else f"part:{p}"

def _load_taxa_index(taxa_jsonl: Path) -> Dict[str, Dict[str, Any]]:
    """Light index: id -> {parent, rank}"""
    out: Dict[str, Dict[str, Any]] = {}
    for obj in read_jsonl(taxa_jsonl):
        out[obj["id"]] = {"parent": obj.get("parent"), "rank": obj.get("rank")}
    return out

def _children_index(taxa: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    ch: Dict[str, List[str]] = {}
    for tid, meta in taxa.items():
        p = meta.get("parent")
        if p:
            ch.setdefault(p, []).append(tid)
    return ch

def _descendants_have_part(start: str, part_id: str, has_part_pairs: Set[Tuple[str, str]], children: Dict[str, List[str]]) -> bool:
    stack = list(children.get(start, []))
    while stack:
        cur = stack.pop()
        if (cur, part_id) in has_part_pairs:
            return True
        stack.extend(children.get(cur, []))
    return False

def _normalize_applies_to(rows: Iterable[Any]) -> List[Dict[str, Any]]:
    return normalize_applies_to(rows)

# --- main --------------------------------------------------------------------

def build_substrates(
    in_dir: Path,         # ontology root (json, rules, compiled taxa)
    tmp_dir: Path,        # build/tmp
    graph_dir: Path,      # build/graph
    verbose: bool = False
):
    ensure_dir(tmp_dir); ensure_dir(graph_dir)

    # Inputs
    taxa_jsonl = graph_dir.parent / "compiled" / "taxa.jsonl"
    # Use compiled snapshot for hermetic builds
    parts_json = graph_dir.parent / "compiled" / "parts.json"
    rules_dir  = in_dir / "rules"
    parts_rules_path   = rules_dir / "parts_applicability.jsonl"
    implied_parts_path = rules_dir / "implied_parts.jsonl"
    tp_policy_path     = rules_dir / "taxon_part_policy.json"
    promoted_parts_path= rules_dir / "promoted_parts.jsonl"

    # Load core data
    taxa = _load_taxa_index(taxa_jsonl)
    children = _children_index(taxa)
    parts = read_json(parts_json)
    part_ids = {p["id"] for p in parts}
    # collect built-in applies_to embedded in parts.json
    builtin_part_rules = [
        {"part": p["id"], "applies_to": p.get("applies_to", [])}
        for p in parts if p.get("applies_to")
    ]

    parts_rules = read_jsonl(parts_rules_path) if parts_rules_path.exists() else []
    for r in parts_rules:
        r["applies_to"] = _normalize_applies_to(r.get("applies_to", []))
        if r.get("exclude"):
            r["exclude"] = _normalize_applies_to(r.get("exclude", []))

    implied_rules = read_jsonl(implied_parts_path) if implied_parts_path.exists() else []
    tp_policy = read_json(tp_policy_path) if tp_policy_path.exists() else {}

    promoted_parts = read_jsonl(promoted_parts_path) if promoted_parts_path.exists() else []

    # Expand applies_to → (taxon_id, part_id)
    all_taxa_ids = set(taxa.keys())

    def _exclude_set(excl) -> set[str]:
        """
        Normalize exclude entries into exact 'tx:...:part:...' strings.
        Supports:
          - "tx:plantae:rosaceae:prunus:domestica:part:fruit"
          - {"taxon_id": "tx:plantae:rosaceae:prunus:domestica", "parts": ["part:fruit","leaf"]}
          - {"taxon_prefix": "...", "parts": [...]}  (treated as exacts)
        """
        out: set[str] = set()
        for e in (excl or []):
            if isinstance(e, str):
                out.add(_strip_colon(e))
            elif isinstance(e, dict):
                tid = _strip_colon(e.get("taxon_id") or e.get("taxon_prefix") or "")
                for p in (e.get("parts") or []):
                    out.add(f"{tid}:{_as_part_id(p)}")
        return out

    def expand_rule(rule: Dict[str, Any]) -> Iterable[Tuple[str, str]]:
        p = rule.get("part")
        if not p:
            return []
        applies = rule.get("applies_to", [])
        exclude = _exclude_set(rule.get("exclude"))
        for ap in applies:
            pref = ap.get("taxon_prefix", "")
            # match all taxa under prefix
            matched = [tid for tid in all_taxa_ids if tid.startswith(pref)]
            tgt_parts = ap.get("parts", []) or [p]
            for tid in matched:
                for pid in tgt_parts:
                    # exclude exact (taxon, part) matches
                    if f"{tid}:{pid}" in exclude:
                        continue
                    yield (tid, p if pid == p else pid)

    # 1) accumulate pairs
    pairs: Set[Tuple[str, str]] = set()
    for r in builtin_part_rules:
        for pair in expand_rule({"part": r["part"], "applies_to": _normalize_applies_to(r["applies_to"]) }):
            pairs.add(pair)
    for r in parts_rules:
        for pair in expand_rule(r):
            pairs.add(pair)

    # 2) optional TP policy (allowlist/blocklist/default by kingdom/rank)
    def _kingdom(tid: str) -> str | None:
        parts = tid.split(":")
        return parts[1] if len(parts) > 2 and parts[0] == "tx" else None

    def policy_allows(tid: str, pid: str) -> bool:
        if not tp_policy:
            return True
        kg = _kingdom(tid)
        rank = taxa[tid]["rank"]
        # blocklist wins
        for b in (tp_policy.get("blocklist") or []):
            if tid.startswith(b.get("taxon_id","")) and pid in (b.get("parts") or []):
                return False
        # allowlist explicit
        for a in (tp_policy.get("allowlist") or []):
            if tid.startswith(a.get("taxon_id","")) and pid in (a.get("parts") or []):
                return True
        # defaults by kingdom/rank
        default_ranks = set((tp_policy.get("default") or {}).get(kg, []))
        return (rank in default_ranks) if default_ranks else True

    pairs = {(t, p) for (t, p) in pairs if (t in taxa) and (p in part_ids) and policy_allows(t, p)}

    # 3) leaf pruning (unless policy allowed earlier)
    kept: Set[Tuple[str, str]] = set()
    for t, p in pairs:
        rank = taxa[t]["rank"]
        kg = _kingdom(t)
        is_leaf = not _descendants_have_part(t, p, pairs, children)
        keep_non_leaf = (kg == "animalia" and rank in ("species", "subspecies"))
        if is_leaf or keep_non_leaf:
            kept.add((t, p))
    pairs = kept

    # implied part lookup for flagging (not changing the pair set)
    implied_idx: Dict[Tuple[str, str], bool] = {}
    for r in implied_rules:
        part_id = r.get("part")
        apps = _normalize_applies_to(r.get("applies_to", []))
        excludes = set(r.get("exclude", []))
        for ap in apps:
            pref = ap["taxon_prefix"]
            for tid, pid in pairs:
                if pid == part_id and tid.startswith(pref) and f"{tid}:{pid}" not in excludes:
                    implied_idx[(tid, pid)] = True

    # 4) OUTPUTS ---------------------------------------------------------------
    # graph/substrates.jsonl : minimal T×P edges
    write_jsonl(graph_dir / "substrates.jsonl", [{"taxon_id": t, "part_id": p} for (t, p) in sorted(pairs)])

    # tmp/tp_index.jsonl : richer TP index used later (naming, filters)
    tp_rows = []
    for (t, p) in sorted(pairs):
        tp_rows.append({
            "tp_id": f"tp:{t}:{p}",
            "taxon_id": t,
            "part_id": p,
            "implied": bool(implied_idx.get((t,p), False))
        })
    write_jsonl(tmp_dir / "tp_index.jsonl", tp_rows)

    # tmp/promoted_parts.valid.jsonl : sanity-checked promoted parts (only part-changing TFs in proto_path)
    # Stage A should have written transforms_canon.json already
    tcanon = read_json(tmp_dir.parent / "tmp" / "transforms_canon.json")
    tdef = {t["id"]: t for t in tcanon}
    # conservative allowlist if class missing
    default_part_changers = {
        "tf:separate","tf:dehull","tf:mill","tf:coagulate","tf:press","tf:split","tf:polish"
    }

    valid_promoted = []
    errors = 0
    for row in promoted_parts:
        ok = True
        pid = row.get("part_id")
        if pid not in part_ids:
            ok = False
        proto = row.get("proto_path") or []
        for step in proto:
            tid = step.get("id")
            if tid not in tdef:
                ok = False; break
            cls = tdef[tid].get("class")
            if cls:
                if cls != "part_changing":
                    ok = False; break
            else:
                if tid not in default_part_changers:
                    ok = False; break
        if ok:
            valid_promoted.append(row)
        else:
            errors += 1

    write_jsonl(tmp_dir / "promoted_parts.valid.jsonl", valid_promoted)

    if verbose:
        print(f"• Substrates: {len(pairs)}  • TP index: {len(tp_rows)}  • Promoted parts accepted: {len(valid_promoted)}  • Promoted parts rejected: {errors}")
