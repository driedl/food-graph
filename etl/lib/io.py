from __future__ import annotations
import json, hashlib, glob
from pathlib import Path
from typing import Iterable, Any, Dict, List, Iterator

def ensure_dir(path: Path) -> None:
    """Ensure directory exists, creating parents if needed."""
    path.mkdir(parents=True, exist_ok=True)

def read_json(p: Path) -> Any:
    """Read JSON file."""
    return json.loads(Path(p).read_text(encoding="utf-8"))

def write_json(p: Path, obj: Any) -> None:
    """Write object to JSON file."""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def read_jsonl(p: Path) -> Iterator[Dict[str, Any]]:
    """Read JSONL file, yielding dictionaries."""
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        yield json.loads(line)

def write_jsonl(p: Path, rows: Iterable[Dict]) -> None:
    """Write rows to JSONL file."""
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

def append_jsonl(p: Path, row: Dict) -> None:
    """Append single row to JSONL file."""
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

def index_jsonl_by(path: Path, key: str) -> Dict[str, Dict[str, Any]]:
    """Read JSONL file and index by specified key."""
    out: Dict[str, Dict[str, Any]] = {}
    for row in read_jsonl(path):
        k = row.get(key)
        if isinstance(k, str):
            out[k] = row
    return out

def sha1_bytes(data: bytes) -> str:
    """Calculate SHA1 hash of bytes."""
    return hashlib.sha1(data).hexdigest()

def file_sha1(path: Path) -> str:
    """Calculate SHA1 hash of file."""
    return sha1_bytes(Path(path).read_bytes())

def hash_of_files(paths: Iterable[Path]) -> str:
    """Calculate combined hash of multiple files."""
    h = hashlib.sha1()
    for p in sorted(set(map(Path, paths))):
        if p.exists():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()

def expand_globs(patterns: Iterable[str]) -> List[Path]:
    """Expand glob patterns to list of paths."""
    paths: List[Path] = []
    for pat in patterns:
        for m in glob.glob(pat, recursive=True):
            paths.append(Path(m))
    return sorted(set(paths))
