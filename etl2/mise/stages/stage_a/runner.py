from __future__ import annotations
import json
from pathlib import Path
from rich.console import Console

from mise.io import ensure_dir, write_json, write_jsonl
from .transform_canon import load_and_canonicalize_transforms
from .rules_normalize import normalize_transform_applicability
from .flags_validate import validate_guarded_flags
from mise.io import read_json, read_jsonl  # shared IO

console = Console()

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
        if verbose: 
            console.print(f"  ✓ transforms_canon.json written ({len(tdefs_canon)} families)", style="green")
    except Exception as e:
        lint["errors"].append(f"TRANSFORMS: {e}")
        if verbose:
            console.print(f"  ❌ Transform canonicalization failed: {e}", style="red")

    # 2) applicability normalization
    try:
        src = in_dir / "rules" / "transform_applicability.jsonl"
        if not src.exists():
            lint["warnings"].append(f"APPLICABILITY: missing {src}")
            norm_rows, n_stats = [], {"input": 0, "output": 0}
            write_jsonl(tmp_dir / "transform_applicability.normalized.jsonl", norm_rows)
            if verbose:
                console.print(f"  ⚠️ Missing {src} → wrote empty transform_applicability.normalized.jsonl", style="yellow")
        else:
            rows = read_jsonl(src)
            norm_rows, n_stats = normalize_transform_applicability(rows)
            write_jsonl(tmp_dir / "transform_applicability.normalized.jsonl", norm_rows)
            if verbose: 
                console.print(f"  ✓ transform_applicability.normalized.jsonl ({len(norm_rows)} rows)", style="green")
        lint["stats"]["transform_applicability"] = n_stats
    except Exception as e:
        lint["errors"].append(f"APPLICABILITY: {e}")
        if verbose:
            console.print(f"  ❌ Applicability normalization failed: {e}", style="red")

    # 3) guarded flags validation
    try:
        rules_path = in_dir / "rules" / "diet_safety_rules.jsonl"
        if not rules_path.exists():
            lint["warnings"].append(f"FLAGS: missing {rules_path}")
            write_json(tmp_dir / "flags.rules.validated.json", {"count": 0, "ok": True})
            if verbose:
                console.print(f"  ⚠️ Missing {rules_path}", style="yellow")
        else:
            parts = read_json(in_dir / "parts.json")
            part_ids = [p["id"] for p in parts]
            tdefs = read_json(tmp_dir / "transforms_canon.json")
            errors, meta = validate_guarded_flags(rules_path, tdefs, part_ids)
            lint["stats"]["flags"] = meta
            write_json(tmp_dir / "flags.rules.validated.json", {"count": meta["count"], "ok": len(errors) == 0})
            for msg in errors: lint["errors"].append(f"FLAGS: {msg}")
            if verbose: 
                console.print(f"  ✓ flags.rules.validated.json ({meta['count']} rules)", style="green")
    except Exception as e:
        lint["errors"].append(f"FLAGS: {e}")
        if verbose:
            console.print(f"  ❌ Flags validation failed: {e}", style="red")

    write_json(rpt_dir / "lint.json", lint)
    if lint["errors"]:
        if verbose: 
            console.print("  ❌ Validation errors found:", style="red")
            for error in lint["errors"]:
                console.print(f"    • {error}", style="red")
        return 1

    return 0
