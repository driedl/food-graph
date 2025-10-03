from __future__ import annotations
import sqlite3, json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set
from datetime import datetime, timezone

from mise.io import read_json, read_jsonl, ensure_dir

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  rank TEXT NOT NULL,
  parent_id TEXT REFERENCES nodes(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_nodes_slug_parent ON nodes(slug, parent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id);

CREATE TABLE IF NOT EXISTS synonyms (
  node_id TEXT REFERENCES nodes(id) ON DELETE CASCADE,
  synonym TEXT NOT NULL,
  PRIMARY KEY (node_id, synonym)
);

CREATE TABLE IF NOT EXISTS part_def (
  id   TEXT PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS has_part (
  taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  part_id  TEXT NOT NULL REFERENCES part_def(id) ON DELETE RESTRICT,
  PRIMARY KEY (taxon_id, part_id)
);

CREATE TABLE IF NOT EXISTS taxon_doc (
  taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  lang TEXT NOT NULL,
  summary TEXT NOT NULL,
  description_md TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  checksum TEXT NOT NULL,
  PRIMARY KEY (taxon_id, lang)
);

-- TP (Taxon+Part)
CREATE TABLE IF NOT EXISTS taxon_part_nodes (
  id TEXT PRIMARY KEY,
  taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  part_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  display_name TEXT NOT NULL,
  slug TEXT NOT NULL,
  rank TEXT NOT NULL DEFAULT 'taxon_part'
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_tp ON taxon_part_nodes(taxon_id, part_id);

-- TPT (Taxon+Part+Transform family canon)
CREATE TABLE IF NOT EXISTS tpt_nodes (
  id TEXT PRIMARY KEY,
  taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  part_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  family TEXT NOT NULL,
  identity_hash TEXT NOT NULL,
  name TEXT,
  synonyms TEXT,
  path_json TEXT NOT NULL  -- identity-only
);

-- Unified search backing table (external content for FTS)
CREATE TABLE IF NOT EXISTS search_content (
  rowid INTEGER PRIMARY KEY,             -- stable handle used by FTS
  ref_type TEXT NOT NULL,                -- 'taxon' | 'tp' | 'tpt'
  ref_id   TEXT NOT NULL,                -- nodes.id | taxon_part_nodes.id | tpt_nodes.id
  taxon_id TEXT,                         -- for filtering/join
  part_id  TEXT,
  family   TEXT,
  entity_rank TEXT,                      -- renamed from 'rank' (reserved keyword)
  name     TEXT NOT NULL,                -- primary display name
  synonyms TEXT,                         -- plain text bag (space-joined)
  display_name TEXT,                     -- optional UI override
  slug     TEXT
);

CREATE INDEX IF NOT EXISTS idx_search_ref ON search_content(ref_type, ref_id);
CREATE INDEX IF NOT EXISTS idx_search_taxon ON search_content(taxon_id);

-- One FTS index across all entity types
CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
  name,          -- col 0: highest weight
  synonyms,      -- col 1
  entity_rank,   -- col 2 (renamed from 'rank' - reserved keyword)
  family,        -- col 3
  content='search_content', content_rowid='rowid',
  tokenize='unicode61 remove_diacritics 2'
);

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, val TEXT NOT NULL);
-- UI metadata for families (tiny helper table for chips/badges)
CREATE TABLE IF NOT EXISTS family_meta (
  id    TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  icon  TEXT,
  color TEXT,
  blurb TEXT
);

-- Per-TPT evaluated flags (safety/diet, etc.)
CREATE TABLE IF NOT EXISTS tpt_flags (
  tpt_id   TEXT NOT NULL REFERENCES tpt_nodes(id) ON DELETE CASCADE,
  flag     TEXT NOT NULL,
  flag_type TEXT NOT NULL,              -- 'safety' | 'dietary' | future
  PRIMARY KEY (tpt_id, flag)
);

-- Lightweight cuisine facets for UI
CREATE TABLE IF NOT EXISTS tpt_cuisines (
  tpt_id  TEXT NOT NULL REFERENCES tpt_nodes(id) ON DELETE CASCADE,
  cuisine TEXT NOT NULL,
  PRIMARY KEY (tpt_id, cuisine)
);

-- 1) Canonical transform defs (from tmp/transforms_canon.json)
CREATE TABLE IF NOT EXISTS transform_def (
  id TEXT PRIMARY KEY,
  name TEXT,
  class TEXT,
  identity INTEGER NOT NULL DEFAULT 0,
  "order" INTEGER NOT NULL DEFAULT 999,
  param_keys TEXT,      -- JSON array: [{key, kind, identity_param, ...}, ...]
  notes TEXT
);

-- 2) Exploded identity steps per TPT (denormalized for speed)
CREATE TABLE IF NOT EXISTS tpt_identity_steps (
  tpt_id   TEXT NOT NULL REFERENCES tpt_nodes(id) ON DELETE CASCADE,
  taxon_id TEXT NOT NULL,   -- copy from tpt_nodes for locality
  part_id  TEXT NOT NULL,   -- copy from tpt_nodes
  step_index INTEGER NOT NULL,
  tf_id    TEXT NOT NULL,
  params_json TEXT NOT NULL, -- normalized dict of identity params only
  PRIMARY KEY (tpt_id, step_index)
);
CREATE INDEX IF NOT EXISTS idx_steps_tf    ON tpt_identity_steps(tf_id);
CREATE INDEX IF NOT EXISTS idx_steps_tp    ON tpt_identity_steps(taxon_id, part_id);
CREATE INDEX IF NOT EXISTS idx_steps_taxon ON tpt_identity_steps(taxon_id);

-- 3) Part synonyms for UI surfacing
CREATE TABLE IF NOT EXISTS part_synonym (
  part_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  synonym TEXT NOT NULL,
  PRIMARY KEY (part_id, synonym)
);

-- 4) Ancestor closure (for fast lineage queries without recursive CTEs at runtime)
CREATE TABLE IF NOT EXISTS taxon_ancestors (
  descendant_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  ancestor_id   TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  depth INTEGER NOT NULL,    -- 0=self, 1=parent, ...
  PRIMARY KEY (descendant_id, ancestor_id)
);

-- 5) Convenience aggregate (optional but very handy)
CREATE TABLE IF NOT EXISTS tp_tf_counts (
  taxon_id TEXT NOT NULL,
  part_id  TEXT NOT NULL,
  tf_id    TEXT NOT NULL,
  count INTEGER NOT NULL,
  PRIMARY KEY (taxon_id, part_id, tf_id)
);
"""

def _last(seg: str) -> str:
    return seg.split(":")[-1].lower()

def _load_rules(in_dir: Path) -> Tuple[List[Dict[str,Any]], List[Dict[str,Any]], List[Dict[str,Any]]]:
    rules_dir = in_dir / "rules"
    implied = read_jsonl(rules_dir / "implied_parts.jsonl") if (rules_dir / "implied_parts.jsonl").exists() else []
    overrides = read_jsonl(rules_dir / "name_overrides.jsonl") if (rules_dir / "name_overrides.jsonl").exists() else []
    tp_syn = read_jsonl(rules_dir / "taxon_part_synonyms.jsonl") if (rules_dir / "taxon_part_synonyms.jsonl").exists() else []
    return implied, overrides, tp_syn

def _load_part_aliases(in_dir: Path) -> Dict[str, List[str]]:
    """rules/part_aliases.jsonl → {part_id: [aliases...]}"""
    path = in_dir / "rules" / "part_aliases.jsonl"
    if not path.exists():
        return {}
    out: Dict[str, List[str]] = {}
    for r in read_jsonl(path):
        pid = r.get("part_id")
        if not isinstance(pid, str): 
            continue
        aliases = [a.strip().lower() for a in (r.get("aliases") or []) if isinstance(a,str) and a.strip()]
        if aliases:
            out[pid] = aliases
    return out

def _load_family_meta(in_dir: Path) -> Dict[str, Dict[str, Any]]:
    path = in_dir / "rules" / "family_meta.json"
    if not path.exists():
        return {}
    obj = read_json(path)
    return obj if isinstance(obj, dict) else {}

def _load_flag_rules(in_dir: Path) -> List[Dict[str, Any]]:
    """rules/diet_safety_rules.jsonl (already validated in Stage A)"""
    path = in_dir / "rules" / "diet_safety_rules.jsonl"
    return read_jsonl(path) if path.exists() else []

def _load_cuisine_map(in_dir: Path) -> List[Dict[str, Any]]:
    """rules/cuisine_map.jsonl"""
    path = in_dir / "rules" / "cuisine_map.jsonl"
    return read_jsonl(path) if path.exists() else []

def _param_get(obj: Dict[str, Any], dotted: str):
    """Simple dotted path resolver inside a dict"""
    cur = obj
    for seg in str(dotted).split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return None
        cur = cur[seg]
    return cur

def _build_identity_index(identity_steps: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """{ transform_id: params_dict } for quick lookup; if multiple, last one wins."""
    idx: Dict[str, Dict[str, Any]] = {}
    for s in identity_steps or []:
        if isinstance(s, dict) and "id" in s:
            idx[s["id"]] = s.get("params") or {}
    return idx

def _eval_condition(cond: Dict[str, Any], id_idx: Dict[str, Dict[str, Any]], part_id: str) -> bool:
    if "has_transform" in cond:
        return cond["has_transform"] in id_idx
    if "has_part" in cond:
        return part_id == cond["has_part"]
    if "param" in cond:
        p = cond["param"]
        if "." not in p:  # must be tf:id.param
            return False
        tf_id, param_path = p.split(".", 1)
        params = id_idx.get(tf_id, {})
        val = _param_get(params, param_path)
        op = cond.get("op")
        if op == "exists":
            return val is not None
        cmpv = cond.get("value")
        if op == "eq":   return val == cmpv
        if op == "ne":   return val != cmpv
        try:
            # numeric-safe compares (leave as-is if not numbers)
            if op in ("gt","gte","lt","lte"):
                return ((val > cmpv) if op=="gt" else
                        (val >= cmpv) if op=="gte" else
                        (val < cmpv) if op=="lt" else
                        (val <= cmpv))
            if op == "in":
                arr = cmpv if isinstance(cmpv, list) else [cmpv]
                return val in arr
            if op == "not_in":
                arr = cmpv if isinstance(cmpv, list) else [cmpv]
                return val not in arr
        except Exception:
            return False
    return False

def _eval_when(when: Dict[str, Any], id_idx: Dict[str, Dict[str, Any]], part_id: str) -> bool:
    if not isinstance(when, dict):
        return False
    ok_all = True
    if "allOf" in when:
        ok_all = all(_eval_condition(c, id_idx, part_id) for c in when["allOf"])
    ok_any = True
    if "anyOf" in when:
        group = when["anyOf"]
        ok_any = any(_eval_condition(c, id_idx, part_id) for c in group) if group else False
    ok_none = True
    if "noneOf" in when:
        ok_none = all(not _eval_condition(c, id_idx, part_id) for c in when["noneOf"])
    return ok_all and ok_any and ok_none

def _is_prefix(pfx: str, s: str) -> bool:
    return s.startswith(pfx)

def _is_implied(taxon_id: str, part_id: str, implied_rules: List[Dict[str,Any]]) -> bool:
    for r in implied_rules:
        if r.get("part") != part_id: 
            continue
        exclude = set(r.get("exclude", []))
        if taxon_id in exclude:
            continue
        for pref in r.get("applies_to", []):
            tp = pref["taxon_prefix"] if isinstance(pref, dict) else str(pref)
            if _is_prefix(tp.rstrip(":"), taxon_id):
                return True
    return False

def _override_name(taxon_id: str, part_id: str, overrides: List[Dict[str,Any]]) -> Tuple[str,str] | None:
    best = None; best_len = -1
    for r in overrides:
        if r.get("part_id") != part_id: 
            continue
        tid = r.get("taxon_id","")
        if tid and _is_prefix(tid, taxon_id) and len(tid) > best_len:
            nm = r.get("name")
            dn = r.get("display_name") or nm
            if nm:
                best = (nm, dn); best_len = len(tid)
    return best

def _tp_extra_synonyms(taxon_id: str, part_id: str, tp_syn_rules: List[Dict[str,Any]]) -> List[str]:
    acc = []
    for r in tp_syn_rules:
        tid = r.get("taxon_id","")
        if r.get("part_id") == part_id and _is_prefix(tid, taxon_id):
            for s in r.get("synonyms",[]) or []:
                if isinstance(s,str) and s.strip():
                    acc.append(s.strip().lower())
    return acc

def build_sqlite(*, in_dir: Path, build_dir: Path, db_path: Path, verbose: bool = False) -> None:
    ensure_dir(db_path.parent)
    con = sqlite3.connect(str(db_path))
    con.executescript(DDL)
    cur = con.cursor()

    # Load compiled pieces
    taxa = read_jsonl(build_dir / "compiled" / "taxa.jsonl")
    docs = read_jsonl(build_dir / "compiled" / "docs.jsonl")
    parts_obj = read_json(build_dir / "compiled" / "parts.json")
    # Accept either array-of-objects ({id,name,...}) or map {id: {...}}
    if isinstance(parts_obj, dict):
        parts_index = {pid: (pdata if isinstance(pdata, dict) else {"name": str(pdata)})
                       for pid, pdata in parts_obj.items()}
    elif isinstance(parts_obj, list):
        parts_index = {p["id"]: p for p in parts_obj if isinstance(p, dict) and "id" in p}
    else:
        parts_index = {}
    substrates = read_jsonl(build_dir / "graph" / "substrates.jsonl")
    tpt = read_jsonl(build_dir / "tmp" / "tpt_canon.jsonl")
    tp_index = read_jsonl(build_dir / "tmp" / "tp_index.jsonl")
    # Rules / UI helpers
    implied_rules, overrides_rules, tp_syn_rules = _load_rules(in_dir)
    part_aliases = _load_part_aliases(in_dir)
    family_meta = _load_family_meta(in_dir)
    flag_rules = _load_flag_rules(in_dir)
    cuisine_map = _load_cuisine_map(in_dir)

    # Insert nodes + synonyms (+collect synonyms for FTS)
    _syn_by_node: Dict[str, List[str]] = {}
    for i, row in enumerate(taxa):
        try:
            tid = row["id"]
            nm = row.get("display_name") or row.get("latin_name") or _last(tid)
            slug = _last(tid)
            rank = row.get("rank", "unknown")
            parent = row.get("parent")
            cur.execute("INSERT OR REPLACE INTO nodes (id, name, slug, rank, parent_id) VALUES (?, ?, ?, ?, ?)",
                       (tid, nm, slug, rank, parent))
            # synonyms
            node_syns: List[str] = []
            for syn in row.get("synonyms", []):
                if isinstance(syn, str) and syn.strip():
                    val = syn.strip().lower()
                    node_syns.append(val)
                    cur.execute("INSERT OR REPLACE INTO synonyms (node_id, synonym) VALUES (?, ?)", (tid, val))
            _syn_by_node[tid] = node_syns
        except Exception as e:
            print(f"Error inserting taxon row {i}: {e}")
            print(f"Row: {row}")
            raise

    for pid, pdata in parts_index.items():
        name = pdata.get("name") if isinstance(pdata, dict) else None
        if name:
            cur.execute("INSERT OR REPLACE INTO part_def (id, name) VALUES (?, ?)", (pid, name))
    
    # Commit base data before inserting dependent records
    con.commit()

    # Insert has_part relationships
    for i, row in enumerate(substrates):
        try:
            cur.execute("INSERT OR REPLACE INTO has_part (taxon_id, part_id) VALUES (?, ?)",
                       (row["taxon_id"], row["part_id"]))
        except Exception as e:
            print(f"Error inserting has_part row {i}: {e}")
            print(f"Row: {row}")
            raise

    # Insert taxon docs
    for row in docs:
        tid = row["taxon_id"]
        lang = row.get("lang", "en")
        summary = row.get("summary", "")
        desc = row.get("description_md", "")
        updated = row.get("updated_at", datetime.now(timezone.utc).isoformat())
        checksum = row.get("checksum", "")
        cur.execute("INSERT OR REPLACE INTO taxon_doc (taxon_id, lang, summary, description_md, updated_at, checksum) VALUES (?, ?, ?, ?, ?, ?)",
                   (tid, lang, summary, desc, updated, checksum))

    # Insert TP nodes (respect name overrides if present)
    for i, row in enumerate(tp_index):
        try:
            tid = row["taxon_id"]
            pid = row["part_id"]
            tp_id = f"{tid}:{pid}"
            # default synthesized name
            default_name = f"{_last(tid)} {parts_index.get(pid, {}).get('name', _last(pid))}"
            ovr = _override_name(tid, pid, overrides_rules)
            if ovr:
                name, display_name = ovr
            else:
                name = row.get("name", default_name)
                display_name = row.get("display_name", name)
            slug = f"{_last(tid)}-{_last(pid)}"
            cur.execute("INSERT OR REPLACE INTO taxon_part_nodes (id, taxon_id, part_id, name, display_name, slug) VALUES (?, ?, ?, ?, ?, ?)",
                       (tp_id, tid, pid, name, display_name, slug))
        except Exception as e:
            print(f"Error inserting TP row {i}: {e}")
            print(f"Row: {row}")
            raise

    # Insert TPT nodes
    for i, row in enumerate(tpt):
        try:
            tid = row["taxon_id"]
            pid = row["part_id"]
            family = row.get("family", "unknown")
            identity_hash = row.get("identity_hash", "")
            # Prefer explicit name; otherwise synthesize a reasonable display name
            name = row.get("name") or f"{_last(tid)} {parts_index.get(pid, {}).get('name', _last(pid))} ({family.lower().replace('_',' ')})"
            synonyms = json.dumps(row.get("synonyms", []))
            # Store the canonical identity-only path (Stage E -> row['identity'])
            path_json = json.dumps(row.get("identity", row.get("path", [])))
            cur.execute("INSERT OR REPLACE INTO tpt_nodes (id, taxon_id, part_id, family, identity_hash, name, synonyms, path_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (row["id"], tid, pid, family, identity_hash, name, synonyms, path_json))
        except Exception as e:
            print(f"Error inserting TPT row {i}: {e}")
            print(f"Row: {row}")
            print(f"taxon_id: {tid}")
            print(f"part_id: {pid}")
            # Check if taxon exists
            cur.execute("SELECT COUNT(*) FROM nodes WHERE id = ?", (tid,))
            taxon_exists = cur.fetchone()[0]
            print(f"Taxon exists: {taxon_exists}")
            # Check if part exists
            cur.execute("SELECT COUNT(*) FROM part_def WHERE id = ?", (pid,))
            part_exists = cur.fetchone()[0]
            print(f"Part exists: {part_exists}")
            raise

    # ----- Unified search materialization ------------------------------------
    def _syn_str(items) -> str:
        if not items:
            return ""
        bag = []
        for s in items:
            if isinstance(s, str):
                s = s.strip().lower()
                if s:
                    bag.append(s)
        # space-joined bag-of-words for FTS
        return " ".join(sorted(set(bag)))

    # Rebuild the external content table deterministically
    cur.execute("DELETE FROM search_content")

    # 1) Taxa → search_content
    for row in taxa:
        tid = row["id"]
        nm = row.get("display_name") or row.get("latin_name") or _last(tid)
        slug = _last(tid)
        rank = row.get("rank", "unknown")
        syns = _syn_str(row.get("synonyms", []))
        cur.execute("""
          INSERT INTO search_content
            (ref_type, ref_id, taxon_id, part_id, family, entity_rank, name, synonyms, display_name, slug)
          VALUES
            ('taxon', ?, ?, NULL, NULL, ?, ?, ?, ?, ?)
        """, (tid, tid, rank, nm, syns, nm, slug))

    # 2) TP nodes → search_content
    #    Use display_name/name from TP table; build synonyms from taxon synonyms + part aliases + TP-specific synonyms
    for row in tp_index:
        tid = row["taxon_id"]; pid = row["part_id"]
        tp_id = f"{tid}:{pid}"
        # name/display_name computed during TP insert
        default_name = f"{_last(tid)} {parts_index.get(pid, {}).get('name', _last(pid))}"
        ovr = _override_name(tid, pid, overrides_rules)
        if ovr:
            name, display_name = ovr
        else:
            name = row.get("name", default_name)
            display_name = row.get("display_name", name)
        slug = f"{_last(tid)}-{_last(pid)}"
        rank = "taxon_part"
        # synonyms bag
        syn_bag = []
        syn_bag.extend(_syn_by_node.get(tid, []))                  # taxon synonyms
        syn_bag.extend(part_aliases.get(pid, []))                  # part aliases
        syn_bag.extend(_tp_extra_synonyms(tid, pid, tp_syn_rules)) # TP-specific synonyms
        syns = _syn_str(syn_bag)
        cur.execute("""
          INSERT INTO search_content
            (ref_type, ref_id, taxon_id, part_id, family, entity_rank, name, synonyms, display_name, slug)
          VALUES
            ('tp', ?, ?, ?, NULL, ?, ?, ?, ?, ?)
        """, (tp_id, tid, pid, rank, name, syns, display_name, slug))

    # 3) TPT nodes → search_content
    for row in tpt:
        ref_id = row["id"]
        tid = row["taxon_id"]; pid = row["part_id"]
        fam = row.get("family", "unknown")
        name = row.get("name") or ""
        syns = _syn_str(row.get("synonyms", []))
        cur.execute("""
          INSERT INTO search_content
            (ref_type, ref_id, taxon_id, part_id, family, entity_rank, name, synonyms, display_name, slug)
          VALUES
            ('tpt', ?, ?, ?, ?, 'tpt', ?, ?, NULL, NULL)
        """, (ref_id, tid, pid, fam, name, syns))

    # (Re)build unified FTS from external content
    cur.execute("INSERT INTO search_fts(search_fts) VALUES('rebuild')")

    # ----- Evaluate and insert per-TPT flags ---------------------------------
    if flag_rules:
        cur.execute("DELETE FROM tpt_flags")
        for row in tpt:
            tpt_id = row["id"]; pid = row["part_id"]
            id_idx = _build_identity_index(row.get("identity", []))
            for rule in flag_rules:
                try:
                    when = rule.get("when") or {}
                    if _eval_when(when, id_idx, pid):
                        flag = rule.get("emit")
                        ftype = rule.get("flag_type", "misc")
                        if isinstance(flag, str) and flag:
                            cur.execute("INSERT OR IGNORE INTO tpt_flags (tpt_id, flag, flag_type) VALUES (?, ?, ?)", (tpt_id, flag, ftype))
                except Exception:
                    # evaluation is best-effort; skip broken rule/row combos
                    continue

    # ----- Evaluate and insert cuisines --------------------------------------
    if cuisine_map:
        cur.execute("DELETE FROM tpt_cuisines")
        # normalize matches so we can check quickly
        norm = []
        for spec in cuisine_map:
            m = spec.get("match") or {}
            tpref = (m.get("taxon_prefix") or "").rstrip(":")
            parts = set(m.get("parts") or [])
            cuisines = [c for c in (spec.get("cuisines") or []) if isinstance(c, str) and c]
            if tpref and cuisines:
                norm.append((tpref, parts, cuisines))
        for row in tpt:
            tpt_id = row["id"]; tid = row["taxon_id"]; pid = row["part_id"]
            for (tpref, parts, cuisines) in norm:
                if tid.startswith(tpref) and (not parts or pid in parts):
                    for c in cuisines:
                        cur.execute("INSERT OR IGNORE INTO tpt_cuisines (tpt_id, cuisine) VALUES (?, ?)", (tpt_id, c))

    # ----- Populate new transform and lineage tables ---------------------------
    
    # 1) Populate transform_def from transforms_canon.json
    tcanon = read_json(build_dir / "tmp" / "transforms_canon.json")
    cur.execute("DELETE FROM transform_def")
    for t in tcanon:
        cur.execute("""
            INSERT OR REPLACE INTO transform_def
              (id, name, class, identity, "order", param_keys, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            t["id"], 
            t.get("name"), 
            t.get("class"),
            1 if t.get("identity") else 0,
            int(t.get("order", 999)),
            json.dumps(t.get("params", [])),
            t.get("notes")
        ))

    # 2) Populate tpt_identity_steps from exploded TPT paths
    cur.execute("DELETE FROM tpt_identity_steps")
    for r in tpt:
        steps = r.get("identity", r.get("path", [])) or []
        for i, s in enumerate(steps):
            if isinstance(s, dict) and "id" in s:
                cur.execute("""
                    INSERT INTO tpt_identity_steps
                      (tpt_id, taxon_id, part_id, step_index, tf_id, params_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    r["id"], 
                    r["taxon_id"], 
                    r["part_id"], 
                    i, 
                    s.get("id"), 
                    json.dumps(s.get("params") or {})
                ))

    # 3) Populate part_synonym from part_aliases
    cur.execute("DELETE FROM part_synonym")
    for pid, aliases in part_aliases.items():
        for a in aliases:
            cur.execute("INSERT OR IGNORE INTO part_synonym(part_id, synonym) VALUES (?, ?)", (pid, a))

    # 4) Populate taxon_ancestors (transitive closure)
    cur.execute("DELETE FROM taxon_ancestors")
    cur.execute("""
        INSERT OR REPLACE INTO taxon_ancestors(descendant_id, ancestor_id, depth)
        WITH RECURSIVE chain(descendant_id, ancestor_id, depth) AS (
          SELECT id, id, 0 FROM nodes
          UNION ALL
          SELECT chain.descendant_id, nodes.parent_id, chain.depth+1
          FROM chain JOIN nodes ON nodes.id = chain.ancestor_id
          WHERE nodes.parent_id IS NOT NULL
        )
        SELECT * FROM chain;
    """)

    # 5) Populate tp_tf_counts (optional pre-agg)
    cur.execute("DELETE FROM tp_tf_counts")
    cur.execute("""
        INSERT INTO tp_tf_counts(taxon_id, part_id, tf_id, count)
        SELECT taxon_id, part_id, tf_id, COUNT(*)
        FROM tpt_identity_steps
        GROUP BY taxon_id, part_id, tf_id
    """)

    # Insert metadata
    cur.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ("build_time", datetime.now(timezone.utc).isoformat()))
    cur.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ("taxa_count", str(len(taxa))))
    cur.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ("parts_count", str(len(parts_index))))
    cur.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ("substrates_count", str(len(substrates))))
    cur.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ("tpt_count", str(len(tpt))))
    cur.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ("schema_version", "2"))

    con.commit()
    # Insert/refresh family UI metadata last (doesn't affect FTS)
    if family_meta:
        for fid, meta in family_meta.items():
            cur.execute(
              "INSERT OR REPLACE INTO family_meta (id, label, icon, color, blurb) VALUES (?, ?, ?, ?, ?)",
              (fid, str(meta.get("label") or fid.title().replace("_"," ")),
                    meta.get("icon"), meta.get("color"), meta.get("blurb"))
            )
        con.commit()
    con.close()
    
    if verbose:
        print(f"  • Packed {len(taxa)} taxa, {len(parts_index)} parts, {len(substrates)} substrates, {len(tpt)} TPTs")
