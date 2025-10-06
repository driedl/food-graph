from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional

@dataclass
class Part:
    id: str
    name: str
    synonyms: List[str]

@dataclass
class Transform:
    id: str
    name: str
    params: List[Dict[str, Any]]  # as defined in transform_def.param_keys

class GraphDB:
    def __init__(self, path: str):
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row

    def parts(self) -> List[Part]:
        q = """
          SELECT p.id, p.name,
                 COALESCE(GROUP_CONCAT(ps.synonym,'\u001f'), '') AS syns
          FROM part_def p
          LEFT JOIN part_synonym ps ON ps.part_id = p.id
          GROUP BY p.id, p.name
        """
        out: List[Part] = []
        for r in self.con.execute(q):
            syns = (r["syns"] or "").split("\u001f") if r["syns"] else []
            out.append(Part(id=r["id"], name=r["name"], synonyms=[s for s in syns if s]))
        return out

    def transforms(self) -> List[Transform]:
        q = """
          SELECT id, name, param_keys
          FROM transform_def
          ORDER BY "order", id
        """
        out: List[Transform] = []
        for r in self.con.execute(q):
            params = []
            try:
                import json
                params = json.loads(r["param_keys"] or "[]")
            except Exception:
                params = []
            out.append(Transform(id=r["id"], name=r["name"], params=params))
        return out

    def search_candidates(self, text: str, topk: int = 15) -> List[Dict[str, Any]]:
        """Return mixed candidates from unified FTS (taxon, tp, tpt)."""
        if not text or not text.strip():
            return []
        
        # Format text for FTS5 query (same as API makeFtsQuery)
        fts_query = ' AND '.join(f"{term}*" for term in text.strip().split() if term)
        
        q = """
          SELECT sc.ref_type, sc.ref_id, sc.name, sc.entity_rank, sc.taxon_id, sc.part_id, sc.family
          FROM search_fts
          JOIN search_content sc ON sc.rowid = search_fts.rowid
          WHERE search_fts MATCH ?
          ORDER BY bm25(search_fts) ASC, sc.entity_rank ASC
          LIMIT ?
        """
        try:
            cur = self.con.execute(q, (fts_query, topk))
            return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            # Fallback to simple LIKE search if FTS fails
            q_fallback = """
              SELECT sc.ref_type, sc.ref_id, sc.name, sc.entity_rank, sc.taxon_id, sc.part_id, sc.family
              FROM search_content sc
              WHERE sc.name LIKE ? OR sc.synonyms LIKE ?
              ORDER BY sc.entity_rank ASC
              LIMIT ?
            """
            cur = self.con.execute(q_fallback, (f"%{text}%", f"%{text}%", topk))
            return [dict(r) for r in cur.fetchall()]

    def id_exists(self, table: str, id_col: str, id_val: str) -> bool:
        q = f"SELECT 1 FROM {table} WHERE {id_col}=? LIMIT 1"
        cur = self.con.execute(q, (id_val,))
        return cur.fetchone() is not None
