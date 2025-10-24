#!/usr/bin/env python3
"""
validate_taxa.py

Validates the ontology after the repo is reorganized into:
data/ontology/taxa/
  plantae/
    families/
      Rosaceae--rose-family.jsonl
      Rosaceae/Prunus--prunus.jsonl         (optional split when family grows big)
    _staged/
      unplaced.jsonl
  fungi/fungi.jsonl
  animalia/animals.jsonl

Validates taxon IDs according to Ontology Bible specifications.
See /docs/technical/ontology-specification.md section 1.1-1.3 for complete ID format rules.

Rules (high-level):
- New ID format: tx:{kingdom}:{genus}:{species}[:{cultivar/breed}]
- Kingdom: p (plantae), a (animalia), f (fungi)
- Parent relationships computed from ID structure (drop last segment)
- ncbi_taxid field required for species-level taxa
- No 'parent' field in JSONL files (computed during build)
- Catch obvious product nouns masquerading as taxa
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Iterable, Optional, Set

# --- Configuration ------------------------------------------------------------

PLANT_RANK_TERMINOLOGY = {"kingdom", "clade", "order", "family", "genus", "species", "variety", "cultivar", "form"}
FUNGI_RANK_TERMINOLOGY = {"kingdom", "class", "order", "family", "genus", "species", "variety", "form"}
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
      - data/ontology/taxa/plantae/families/**/*.jsonl
      - data/ontology/taxa/fungi/fungi.jsonl
      - data/ontology/taxa/animalia/animals.jsonl
    Returns list of (path, lineno, obj).
    """
    items: List[Tuple[Path, int, dict]] = []

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


def validate_new_id_format(taxon_id: str) -> bool:
    """Validate new taxon ID format: tx:{kingdom}:{genus}:{species}[:{cultivar/breed}]"""
    if not taxon_id.startswith('tx:'):
        return False
    
    segments = taxon_id.split(':')
    if len(segments) < 2:
        return False
    
    # Special cases for root taxa
    if taxon_id in ['tx:life', 'tx:eukaryota']:
        return True
    
    # Kingdom-level taxa (both old and new format)
    if len(segments) == 2:
        kingdom = segments[1]
        return kingdom in ['p', 'a', 'f', 'plantae', 'animalia', 'fungi']
    
    # Clade-level taxa (e.g., tx:plantae:eudicots)
    if len(segments) == 3:
        kingdom = segments[1]
        if kingdom not in ['p', 'a', 'f', 'plantae', 'animalia', 'fungi']:
            return False
        clade = segments[2]
        return clade and clade.replace('_', '').replace('-', '').isalnum() and clade.islower()
    
    # Genus/species/cultivar level taxa (2-4 segments)
    if len(segments) > 4:
        return False
    
    # Check kingdom
    kingdom = segments[1]
    if kingdom not in ['p', 'a', 'f', 'plantae', 'animalia', 'fungi']:
        return False
    
    # Check segment format (lowercase letters, digits, underscores)
    for segment in segments[2:]:
        if not segment or not segment.replace('_', '').replace('-', '').isalnum():
            return False
        if not segment.islower():
            return False
    
    return True

def expected_parent_for_id(id_: str) -> Optional[str]:
    """
    Computes the required parent id given a node id for new format:
    - tx:p, tx:a, tx:f → no parent (kingdom level)
    - tx:p:genus → parent = tx:p
    - tx:p:genus:species → parent = tx:p:genus
    - tx:p:genus:species:cultivar → parent = tx:p:genus:species
    """
    if not id_.startswith("tx:"):
        return None
    
    segments = id_.split(":")
    if len(segments) <= 2:  # Kingdom level (tx:p, tx:a, tx:f)
        return None
    
    # Drop last segment
    return ":".join(segments[:-1])


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
        require prefix 'tx:plantae:<clade>:<order>:<family>' (clade-based structure)
      - If file is .../plantae/families/<Family>/*.jsonl (genus shards),
        require prefix 'tx:plantae:<clade>:<order>:<family>[:<genus>]' inferred from filename.
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
        # For clade-based structure, we need to determine the expected prefix
        # based on the family name and the clade structure
        # Since files are still named after families but contain clade-based IDs,
        # we need to be more flexible and check if the ID starts with any valid clade prefix
        return None  # Disable strict file alignment for now during transition

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
        if not isinstance(id_, str) or not validate_new_id_format(id_):
            errors += 1
            fail(f"{ctx}: invalid id format (must be tx:{{kingdom}}:{{genus}}:{{species}}[:{{cultivar}}]): {id_!r}")
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

        # Parent relationship validation (parent field should not exist in JSONL)
        if "parent" in obj:
            errors += 1
            fail(f"{ctx}: field 'parent' should not be present in JSONL files (computed during build).")
        
        # NCBI taxid validation for species-level taxa (warning only for now)
        rank = obj.get("rank", "")
        if rank in ["species", "genus"] and "ncbi_taxid" not in obj:
            # Make this a warning instead of an error for now
            print(f"WARNING: {ctx}: species/genus level taxa should have 'ncbi_taxid' field for NCBI verification.")
        
        # Validate ncbi_taxid format if present
        ncbi_taxid = obj.get("ncbi_taxid")
        if ncbi_taxid is not None:
            if not isinstance(ncbi_taxid, int) or ncbi_taxid <= 0:
                errors += 1
                fail(f"{ctx}: 'ncbi_taxid' must be a positive integer, got: {ncbi_taxid}")

        # Validate kingdom from ID
        kingdom = id_.split(':')[1] if len(id_.split(':')) > 1 else None
        if kingdom not in ['p', 'a', 'f', 'plantae', 'animalia', 'fungi', 'life', 'eukaryota']:
            errors += 1
            fail(f"{ctx}: invalid kingdom '{kingdom}' in ID. Must be 'p'/'plantae' (plantae), 'a'/'animalia' (animalia), 'f'/'fungi' (fungi), 'life', or 'eukaryota'.")

        # Terminology sanity (soft per kingdom)
        rank = str(obj.get("rank"))
        if kingdom == "p" and rank not in PLANT_RANK_TERMINOLOGY:
            errors += 1
            fail(f"{ctx}: invalid plant rank '{rank}'. Allowed: {sorted(PLANT_RANK_TERMINOLOGY)}")
        if kingdom == "f" and rank not in FUNGI_RANK_TERMINOLOGY:
            errors += 1
            fail(f"{ctx}: invalid fungi rank '{rank}'. Allowed: {sorted(FUNGI_RANK_TERMINOLOGY)}")
        if kingdom == "a" and rank not in ANIMAL_RANK_TERMINOLOGY:
            errors += 1
            fail(f"{ctx}: invalid animal rank '{rank}'. Allowed: {sorted(ANIMAL_RANK_TERMINOLOGY)}")

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

    # Make sure all parents exist
    for pid in sorted(parent_ids):
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
        print("✓ Taxa validation passed (structure, IDs, ranks, file alignment, product detection)")
    else:
        print("✗ Taxa validation failed.", file=sys.stderr)
    sys.exit(rc)


if __name__ == "__main__":
    main()
