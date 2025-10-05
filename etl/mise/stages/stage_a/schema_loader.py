# -*- coding: utf-8 -*-
from __future__ import annotations
import json, io
from pathlib import Path
from typing import Iterable, List, Tuple, Dict, Any

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _strip_comments_and_bom(text: str) -> str:
    # Remove UTF-8 BOM and strip //-comment lines in JSONL usage (handled line-by-line below)
    return text.replace("\ufeff", "")

def read_json(path: Path) -> Any:
    try:
        data = _strip_comments_and_bom(path.read_text(encoding="utf-8"))
        return json.loads(data)
    except FileNotFoundError:
        raise FileNotFoundError(f"Missing JSON file: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: invalid JSON: {e}") from e

def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for i, raw in enumerate(f, 1):
                line = _strip_comments_and_bom(raw).strip()
                if not line or line.startswith("//"):
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"{path}:{i}: invalid JSONL: {e}") from e
                if not isinstance(obj, dict):
                    raise ValueError(f"{path}:{i}: expected object per line")
                out.append(obj)
    except FileNotFoundError:
        raise FileNotFoundError(f"Missing JSONL file: {path}")
    return out

def write_json(path: Path, obj: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True))

def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")
