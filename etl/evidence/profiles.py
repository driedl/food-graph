from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from .lib.jsonl import read_jsonl
from .db import GraphDB

# NOTE: This is intentionally a stub for now.
# It demonstrates how we'd fold JSONL evidence into the SQLite DB later.

def main():
    ap = argparse.ArgumentParser(prog="evidence-profiles", description="(Stub) Insert accepted evidence into graph DB.")
    ap.add_argument("--graph", default="etl2/build/database/graph.dev.sqlite")
    ap.add_argument("--evidence", default="data/evidence/fdc-foundation")
    ap.add_argument("--accept-threshold", type=float, default=0.7)
    args = ap.parse_args()

    ev_dir = Path(args.evidence)
    foods = list(read_jsonl(ev_dir / "foods.jsonl") or [])
    nutrients = list(read_jsonl(ev_dir / "nutrients.jsonl") or [])
    mappings = list(read_jsonl(ev_dir / "mapping.jsonl") or [])

    # Filter accepted mappings
    by_food = { m.get("food_id"): m for m in mappings if (m.get("confidence") or 0) >= args.accept_threshold and m.get("identity_json") }
    accepted_food_ids = set(by_food.keys())
    accepted_nutrients = [n for n in nutrients if n.get("food_id") in accepted_food_ids]

    # TODO: Map nutrient names → canonical nutr ids (using a registry file or DB lookup)
    # TODO: Create tables if missing: nutrition_profile_current, nutrition_profile_provenance
    # TODO: Insert provenance rows; compute/merge "current" rows per Node×Nutrient based on rules

    print(f"[profiles] accepted foods: {len(accepted_food_ids)}")
    print(f"[profiles] accepted nutrient rows: {len(accepted_nutrients)}")
    print("[profiles] TODO: implement DB upsert logic here (kept as a POC stub)")

if __name__ == "__main__":
    main()
