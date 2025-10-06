from __future__ import annotations
from pathlib import Path
from typing import Dict, Iterator, Any
from lib.io import write_jsonl as _write_jsonl, append_jsonl as _append_jsonl, read_jsonl as _read_jsonl, index_jsonl_by as _index_jsonl_by

# Re-export shared utilities for backward compatibility
def write_jsonl(path: Path, rows) -> None:
    _write_jsonl(path, rows)

def append_jsonl(path: Path, row: Dict) -> None:
    _append_jsonl(path, row)

def read_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    return _read_jsonl(path)

def index_jsonl_by(path: Path, key: str) -> Dict[str, Dict[str, Any]]:
    return _index_jsonl_by(path, key)
