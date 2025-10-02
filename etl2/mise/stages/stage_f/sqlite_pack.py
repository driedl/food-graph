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

-- Keep a lightweight 'id' field in FTS so results can be resolved by callers.
CREATE VIRTUAL TABLE IF NOT EXISTS taxa_fts USING fts5(id, name, synonyms, taxon_rank, content='',
             tokenize='unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE IF NOT EXISTS tp_fts USING fts5(id, name, tp_rank, content='',
             tokenize='unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE IF NOT EXISTS tpt_fts USING fts5(id, name, family, content='',
             tokenize='unicode61 remove_diacritics 2');

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, val TEXT NOT NULL);
"""

def _last(seg: str) -> str:
    return seg.split(":")[-1].lower()

def _load_rules(in_dir: Path) -> Tuple[List[Dict[str,Any]], List[Dict[str,Any]], List[Dict[str,Any]]]:
    rules_dir = in_dir / "rules"
    implied = read_jsonl(rules_dir / "implied_parts.jsonl") if (rules_dir / "implied_parts.jsonl").exists() else []
    overrides = read_jsonl(rules_dir / "name_overrides.jsonl") if (rules_dir / "name_overrides.jsonl").exists() else []
    tp_syn = read_jsonl(rules_dir / "taxon_part_synonyms.jsonl") if (rules_dir / "taxon_part_synonyms.jsonl").exists() else []
    return implied, overrides, tp_syn

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

    # Insert TP nodes
    for i, row in enumerate(tp_index):
        try:
            tid = row["taxon_id"]
            pid = row["part_id"]
            tp_id = f"{tid}:{pid}"
            name = row.get("name", f"{_last(tid)} {parts_index.get(pid, {}).get('name', _last(pid))}")
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

    # Build/populate FTS (contentless FTS5)
    # taxa_fts(id,name,synonyms,taxon_rank)
    for row in taxa:
        tid = row["id"]
        nm = row.get("display_name") or row.get("latin_name") or _last(tid)
        r  = row.get("rank", "unknown")
        syn_text = " ".join(_syn_by_node.get(tid, []))
        cur.execute("INSERT INTO taxa_fts(id, name, synonyms, taxon_rank) VALUES (?, ?, ?, ?)", (tid, nm, syn_text, r))
    # tp_fts(id,name,tp_rank)
    for row in tp_index:
        tp_id = f"{row['taxon_id']}:{row['part_id']}"
        nm = row.get("display_name") or row.get("name") or tp_id
        cur.execute("INSERT INTO tp_fts(id, name, tp_rank) VALUES (?, ?, ?)", (tp_id, nm, "taxon_part"))
    # tpt_fts(id,name,family)
    for row in tpt:
        nm = row.get("name") or ""
        fam = row.get("family", "")
        cur.execute("INSERT INTO tpt_fts(id, name, family) VALUES (?, ?, ?)", (row["id"], nm, fam))

    # Insert metadata
    cur.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ("build_time", datetime.now(timezone.utc).isoformat()))
    cur.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ("taxa_count", str(len(taxa))))
    cur.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ("parts_count", str(len(parts_index))))
    cur.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ("substrates_count", str(len(substrates))))
    cur.execute("INSERT OR REPLACE INTO meta (key, val) VALUES (?, ?)", ("tpt_count", str(len(tpt))))

    con.commit()
    con.close()
    
    if verbose:
        print(f"  • Packed {len(taxa)} taxa, {len(parts_index)} parts, {len(substrates)} substrates, {len(tpt)} TPTs")
