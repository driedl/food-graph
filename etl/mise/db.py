from __future__ import annotations
import sqlite3
from pathlib import Path

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
-- Keep this intentionally tiny for the stub; real schema will arrive with stages
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, val TEXT NOT NULL);
"""

def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.executescript(DDL)
    return con

def set_meta(con, key: str, val: str) -> None:
    con.execute("INSERT OR REPLACE INTO meta(key,val) VALUES(?,?)", (key, val))
    con.commit()
