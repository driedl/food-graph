from __future__ import annotations
from pathlib import Path
from typing import Iterable, Any, Dict, List
from lib.io import (
    ensure_dir as _ensure_dir,
    read_json as _read_json,
    write_json as _write_json,
    read_jsonl as _read_jsonl,
    write_jsonl as _write_jsonl,
    sha1_bytes as _sha1_bytes,
    file_sha1 as _file_sha1,
    hash_of_files as _hash_of_files,
    expand_globs as _expand_globs
)

# Re-export shared utilities for backward compatibility
def ensure_dir(path: Path) -> None:
    _ensure_dir(path)

def read_json(p: Path) -> Any:
    return _read_json(p)

def write_json(p: Path, obj: Any) -> None:
    _write_json(p, obj)

def read_jsonl(p: Path) -> List[Dict]:
    return list(_read_jsonl(p))

def write_jsonl(p: Path, rows: Iterable[Dict]) -> None:
    _write_jsonl(p, rows)

def sha1_bytes(data: bytes) -> str:
    return _sha1_bytes(data)

def file_sha1(path: Path) -> str:
    return _file_sha1(path)

def hash_of_files(paths: Iterable[Path]) -> str:
    return _hash_of_files(paths)

def expand_globs(patterns: Iterable[str]) -> List[Path]:
    return _expand_globs(patterns)
