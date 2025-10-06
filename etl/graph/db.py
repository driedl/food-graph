from __future__ import annotations
import sqlite3
from pathlib import Path
from lib.db import open_db as _open_db, set_meta as _set_meta

# Re-export shared utilities for backward compatibility
def open_db(path: Path) -> sqlite3.Connection:
    return _open_db(path)

def set_meta(con, key: str, val: str) -> None:
    _set_meta(con, key, val)
