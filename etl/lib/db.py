from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager

class DatabaseConnection:
    """Shared database connection utilities for SQLite operations."""
    
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.con = sqlite3.connect(str(self.path))
        self.con.row_factory = sqlite3.Row
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.con.rollback()
        else:
            self.con.commit()
        self.con.close()
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries."""
        try:
            cur = self.con.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise DatabaseError(f"Query failed: {e}")
    
    def execute_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute a query and return single result as dictionary."""
        try:
            cur = self.con.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None
        except Exception as e:
            raise DatabaseError(f"Query failed: {e}")
    
    def id_exists(self, table: str, id_col: str, id_val: str) -> bool:
        """Check if an ID exists in a table."""
        query = f"SELECT 1 FROM {table} WHERE {id_col}=? LIMIT 1"
        try:
            cur = self.con.execute(query, (id_val,))
            return cur.fetchone() is not None
        except Exception as e:
            # Log error but don't fail - useful for validation
            return False
    
    def execute_script(self, script: str) -> None:
        """Execute a SQL script."""
        try:
            self.con.executescript(script)
        except Exception as e:
            raise DatabaseError(f"Script execution failed: {e}")
    
    def commit(self) -> None:
        """Commit the current transaction."""
        self.con.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.con.rollback()

class DatabaseError(Exception):
    """Database operation error."""
    pass

def open_db(path: Path) -> sqlite3.Connection:
    """Open a database connection with basic setup."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    
    # Basic setup
    con.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, val TEXT NOT NULL);
    """)
    return con

def set_meta(con: sqlite3.Connection, key: str, val: str) -> None:
    """Set a metadata value."""
    con.execute("INSERT OR REPLACE INTO meta(key,val) VALUES(?,?)", (key, val))
    con.commit()

@contextmanager
def db_transaction(con: sqlite3.Connection):
    """Context manager for database transactions."""
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
