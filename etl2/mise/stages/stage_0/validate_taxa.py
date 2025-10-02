#!/usr/bin/env python3
"""
validate_taxa.py

Validates the ontology after the repo is reorganized into:
data/ontology/taxa/
  index.jsonl
  plantae/
    families/
      Rosaceae--rose-family.jsonl
      Rosaceae/Prunus--prunus.jsonl         (optional split when family grows big)
    _staged/
      unplaced.jsonl
  fungi/fungi.jsonl
  animalia/animals.jsonl

Rules (high-level):
- Strict, contiguous ID paths (no parent skipping). Parent must exist for every node except tx:life.
- No 'tags' field anywhere.
- Plants: no 'order' rank anywhere; families live directly under tx:plantae.
- File alignment: every item in a family shard starts with that family's ID; every item in a genus shard starts with that genus' ID.
- If _staged/unplaced.jsonl exists and is non-empty → fail.
- Catch obvious product nouns masquerading as taxa (e.g., Brown Sugar, Powdered Sugar, Granulated Sugar).
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Iterable, Optional, Set

# --- Configuration ------------------------------------------------------------

PLANT_RANK_TERMINOLOGY = {"kingdom", "family", "genus", "species", "variety", "cultivar", "form"}
FUNGI_RANK_TERMINOLOGY = {"kingdom", "genus", "species", "variety", "form"}
ANIMAL_RANK_TERMINOLOGY = {
    # Be permissive for mid-ranks so we can support full biological paths
    "kingdom", "phylum", "class", "order", "suborder", "infraorder",
    "family", "subfamily", "tribe", "subtribe", "genus", "species"
}

# Species-level "obvious product" bans (expand as needed)
BANNED_PRODUCT_DISPLAY_NAMES = {
    "Brown Sugar",
    "Powdered Sugar",
    "Granulated Sugar",
    "Granulated Sugar (beet)",
    "Granulated Sugar (cane)",
    "Coconut Sugar",
    "Date Sugar",
}

# --- Helpers -----------------------------------------------------------------

def iter_jsonl(path: Path) -> Iterable[Tuple[int, dict]]:
    """
    Yields (lineno, obj) for each JSONL line in path. Lines beginning with // are skipped.
    """
    with path.open("r", encoding="utf-8") as f:
        for i, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{i}: invalid JSON: {e}") from e
            yield i, obj


def is_under(p: Path, *parts: str) -> bool:
    try:
        idx = p.parts.index(parts[0])
    except ValueError:
        return False
    return p.parts[idx:idx+len(parts)] == parts


def read_all_taxa(root: Path) -> List[Tuple[Path, int, dict]]:
    """
    Reads JSONL objects from:
      - data/ontology/taxa/index.jsonl
      - data/ontology/taxa/plantae/families/**/*.jsonl
      - data/ontology/taxa/fungi/fungi.jsonl
      - data/ontology/taxa/animalia/animals.jsonl
    Returns list of (path, lineno, obj).
    """
    items: List[Tuple[Path, int, dict]] = []

    index = root / "index.jsonl"
    if index.exists():
        for ln, obj in iter_jsonl(index):
            items.append((index, ln, obj))

    # plantae families and (optional) genus shards
    for f in sorted((root / "plantae" / "families").rglob("*.jsonl")):
        for ln, obj in iter_jsonl(f):
            items.append((f, ln, obj))

    fungi = root / "fungi" / "fungi.jsonl"
    if fungi.exists():
        for ln, obj in iter_jsonl(fungi):
            items.append((fungi, ln, obj))

    animals = root / "animalia" / "animals.jsonl"
    if animals.exists():
        for ln, obj in iter_jsonl(animals):
            items.append((animals, ln, obj))

    return items


def expected_parent_for_id(id_: str) -> Optional[str]:
    """
    Computes the required parent id given a node id, based on the "tx:" namespace
    and our path rule:
      - tx:life → no parent
      - tx:eukaryota → parent = tx:life
      - tx:<kingdom> → parent = tx:eukaryota
      - deeper: drop the last taxon segment (after 'tx').

    Returns None if this is the root (tx:life).
    """
    parts = id_.split(":")
    if len(parts) < 2 or parts[0] != "tx":
        return None  # will be flagged elsewhere as malformed
    tail = parts[1:]

    # Handle root/domain explicitly
    if id_ == "tx:life":
        return None
    if id_ == "tx:eukaryota":
        return "tx:life"

    if len(tail) == 1:
        # kingdom
        return "tx:eukaryota"

    # deeper (kingdom or lower) → previous segment
    return "tx:" + ":".join(tail[:-1])


def kingdom_from_id(id_: str) -> Optional[str]:
    parts = id_.split(":")
    if len(parts) < 3 or parts[0] != "tx":
        return None
    return parts[1]  # kingdom name for kingdom-or-lower nodes


def prefix_for_file_alignment(path: Path, obj: dict) -> Optional[str]:
    """
    For family/genus shard files, determine the required id prefix that all
    rows in this file must share.

    Strategy:
      - If file is data/ontology/taxa/plantae/families/<Family>.jsonl
        require prefix 'tx:plantae:<family>'
      - If file is .../plantae/families/<Family>/*.jsonl (genus shards),
        require prefix 'tx:plantae:<family>[:<genus>]' inferred from filename.
        We derive <family> from the parent folder name, and (for genus shards)
        <genus> from the file's Latin prefix before the delimiter (-- or :)
        or before first dot.
      - For other files, return None (no alignment check).
    """
    try:
        idx = path.parts.index("plantae")
    except ValueError:
        return None
    # Expect .../plantae/families/...
    sub = path.parts[idx:]
    if len(sub) < 3 or sub[1] != "families":
        return None

    # Case 1: direct family file under families/
    if path.parent.name == "families":
        # Take the Latin family from filename start (before delimiter or dot)
        latin_family = path.stem.split("--", 1)[0].split(":", 1)[0]
        return f"tx:plantae:{latin_family.lower()}"

    # Case 2: genus shard inside a family subfolder
    latin_family = path.parent.name  # the folder name should be exactly 'Rosaceae'
    family_prefix = f"tx:plantae:{latin_family.lower()}"
    # Genus Latin from filename before delimiter or dot
    latin_genus = path.stem.split("--", 1)[0].split(":", 1)[0]
    return f"{family_prefix}:{latin_genus.lower()}"


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


# --- Main validation ----------------------------------------------------------

def validate(root: Path) -> int:
    errors = 0

    taxa: List[Tuple[Path, int, dict]] = read_all_taxa(root)
    if not taxa:
        fail(f"No taxa found under {root}. Did you run from repo root?")
        return 1

    # Block if staged/unplaced has content
    staged = root / "plantae" / "_staged" / "unplaced.jsonl"
    if staged.exists():
        has_any = any(True for _ in iter_jsonl(staged))
        if has_any:
            errors += 1
            fail(f"{staged}: must be empty before commit (staged/unplaced contains rows).")

    by_id: Dict[str, Tuple[Path, int, dict]] = {}
    parent_ids: Set[str] = set()
    seen_paths: Dict[Path, str] = {}  # required prefix per file

    for path, ln, obj in taxa:
        ctx = f"{path}:{ln}"

        # Required fields
        for key in ("id", "rank", "display_name", "latin_name"):
            if key not in obj:
                errors += 1
                fail(f"{ctx}: missing required field '{key}'")

        id_ = obj.get("id")
        if not isinstance(id_, str) or not id_.startswith("tx:") or ":" not in id_:
            errors += 1
            fail(f"{ctx}: invalid id format (must start with 'tx:' and include path segments): {id_!r}")
            continue

        # No 'tags'
        if "tags" in obj:
            errors += 1
            fail(f"{ctx}: field 'tags' is not allowed; remove it.")

        # Unique ids
        if id_ in by_id:
            other_path, other_ln, _ = by_id[id_]
            errors += 1
            fail(f"{ctx}: duplicate id with {other_path}:{other_ln}: {id_}")
        else:
            by_id[id_] = (path, ln, obj)

        # Parent relationship & contiguous path
        exp_parent = expected_parent_for_id(id_)
        parent = obj.get("parent")
        if exp_parent is None:
            # only tx:life should hit this
            if id_ != "tx:life" and id_ != "tx":
                errors += 1
                fail(f"{ctx}: unexpected root-like id {id_}; only 'tx:life' may omit a parent.")
        else:
            if parent != exp_parent:
                errors += 1
                fail(f"{ctx}: parent must be '{exp_parent}' (derived from id), got '{parent}'.")

            if parent:
                parent_ids.add(parent)

        # Prohibit 'order' rank under plants
        k = kingdom_from_id(id_)
        if k == "plantae" and obj.get("rank") == "order":
            errors += 1
            fail(f"{ctx}: plants may not have rank 'order'. Reparent families directly under tx:plantae and update ids.")

        # Terminology sanity (soft per kingdom)
        rank = str(obj.get("rank"))
        if k == "plantae" and rank not in PLANT_RANK_TERMINOLOGY:
            errors += 1
            fail(f"{ctx}: invalid plant rank '{rank}'. Allowed: {sorted(PLANT_RANK_TERMINOLOGY)}")
        if k == "fungi" and rank not in FUNGI_RANK_TERMINOLOGY:
            errors += 1
            fail(f"{ctx}: invalid fungi rank '{rank}'. Allowed: {sorted(FUNGI_RANK_TERMINOLOGY)}")
        if k == "animalia" and rank not in ANIMAL_RANK_TERMINOLOGY:
            errors += 1
            fail(f"{ctx}: invalid animal rank '{rank}'. Allowed: {sorted(ANIMAL_RANK_TERMINOLOGY)}")
        if k is None:
            # index.jsonl items: tx:life (root), tx:eukaryota (domain), tx:<kingdom> (kingdom)
            if id_ not in {"tx:life", "tx:eukaryota"} and rank != "kingdom":
                errors += 1
                fail(f"{ctx}: unexpected item outside a kingdom: id={id_}, rank={rank}")

        # Family/genus file alignment (only enforced for plantae shards)
        req_prefix = prefix_for_file_alignment(path, obj)
        if req_prefix:
            prev = seen_paths.get(path)
            if prev is None:
                seen_paths[path] = req_prefix  # remember required prefix for this file
            else:
                # stick with the initial requirement (should be same)
                req_prefix = prev
            if not id_.startswith(req_prefix + ":") and id_ != req_prefix:
                errors += 1
                fail(f"{ctx}: id must start with '{req_prefix}' for file alignment. Got '{id_}'.")

        # Product nouns masquerading as species (display_name check)
        if rank in {"species", "variety", "cultivar", "form"}:
            dn = str(obj.get("display_name", "")).strip()
            if dn in BANNED_PRODUCT_DISPLAY_NAMES:
                errors += 1
                fail(f"{ctx}: looks like a product ('{dn}') not a biological taxon. Remove from taxa; model as a transform/product elsewhere.")

    # Make sure all parents exist (except tx:life)
    for pid in sorted(parent_ids):
        if pid == "tx:life":
            # allowed to be missing parent
            if pid not in by_id:
                errors += 1
                fail(f"index.jsonl: missing tx:life (required parent).")
            continue
        if pid not in by_id:
            errors += 1
            fail(f"Missing parent node: {pid}")

    return 0 if errors == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taxa-root", default="data/ontology/taxa", help="Path to data/ontology/taxa/")
    args = ap.parse_args()
    root = Path(args.taxa_root)

    rc = validate(root)
    if rc == 0:
        print("✓ Validation passed.")
    else:
        print("✗ Validation failed.", file=sys.stderr)
    sys.exit(rc)


if __name__ == "__main__":
    main()
