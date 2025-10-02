from __future__ import annotations
import json
from pathlib import Path

from mise.io import ensure_dir, write_json, write_jsonl
from .transform_canon import load_and_canonicalize_transforms
from .rules_normalize import normalize_transform_applicability
from .flags_validate import validate_guarded_flags
from mise.io import read_json, read_jsonl  # shared IO

def run(in_dir: Path, build_dir: Path, verbose: bool = False) -> int:
    tmp_dir = build_dir / "tmp"
    rpt_dir = build_dir / "report"
    ensure_dir(tmp_dir); ensure_dir(rpt_dir)

    lint = {"errors": [], "warnings": [], "stats": {}}

    # 1) transforms canonicalization
    try:
        tdefs_canon, tstats = load_and_canonicalize_transforms(in_dir)
        write_json(tmp_dir / "transforms_canon.json", tdefs_canon)
        lint["stats"]["transforms"] = tstats
        if verbose: print(f"✓ transforms_canon.json written ({len(tdefs_canon)} families)")
    except Exception as e:
        lint["errors"].append(f"TRANSFORMS: {e}")

    # 2) applicability normalization
    try:
        src = in_dir / "rules" / "transform_applicability.jsonl"
        if not src.exists():
            lint["warnings"].append(f"APPLICABILITY: missing {src}")
            norm_rows, n_stats = [], {"input": 0, "output": 0}
        else:
            rows = read_jsonl(src)
            norm_rows, n_stats = normalize_transform_applicability(rows)
            write_jsonl(tmp_dir / "transform_applicability.normalized.jsonl", norm_rows)
            if verbose: print(f"✓ transform_applicability.normalized.jsonl ({len(norm_rows)} rows)")
        lint["stats"]["transform_applicability"] = n_stats
    except Exception as e:
        lint["errors"].append(f"APPLICABILITY: {e}")

    # 3) guarded flags validation
    try:
        rules_path = in_dir / "rules" / "diet_safety_rules.jsonl"
        if not rules_path.exists():
            lint["warnings"].append(f"FLAGS: missing {rules_path}")
            write_json(tmp_dir / "flags.rules.validated.json", {"count": 0, "ok": True})
        else:
            parts = read_json(in_dir / "parts.json")
            part_ids = [p["id"] for p in parts]
            tdefs = read_json(tmp_dir / "transforms_canon.json")
            errors, meta = validate_guarded_flags(rules_path, tdefs, part_ids)
            lint["stats"]["flags"] = meta
            write_json(tmp_dir / "flags.rules.validated.json", {"count": meta["count"], "ok": len(errors) == 0})
            for msg in errors: lint["errors"].append(f"FLAGS: {msg}")
            if verbose: print(f"✓ flags.rules.validated.json (rules={meta['count']})")
    except Exception as e:
        lint["errors"].append(f"FLAGS: {e}")

    write_json(rpt_dir / "lint.json", lint)
    if lint["errors"]:
        if verbose: print(json.dumps(lint, indent=2, ensure_ascii=False))
        print("✗ Stage A failed — see etl2/build/report/lint.json")
        return 1

    print("✓ Stage A completed cleanly")
    return 0
