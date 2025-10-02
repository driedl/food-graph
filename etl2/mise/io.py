from __future__ import annotations
import json, hashlib, glob
from pathlib import Path
from typing import Iterable, Any, Dict, List

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))

def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def read_jsonl(p: Path) -> List[Dict]:
    out = []
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        out.append(json.loads(line))
    return out

def write_jsonl(p: Path, rows: Iterable[Dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

def sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()

def file_sha1(path: Path) -> str:
    return sha1_bytes(Path(path).read_bytes())

def hash_of_files(paths: Iterable[Path]) -> str:
    h = hashlib.sha1()
    for p in sorted(set(map(Path, paths))):
        if p.exists():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()

def expand_globs(patterns: Iterable[str]) -> List[Path]:
    paths: List[Path] = []
    for pat in patterns:
        for m in glob.glob(pat, recursive=True):
            paths.append(Path(m))
    return sorted(set(paths))
