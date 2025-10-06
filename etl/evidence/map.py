from __future__ import annotations
import argparse, json, os, sys, re, time
from pathlib import Path
from typing import Dict, Any, List, Iterable
from datetime import datetime
from jsonschema import validate, ValidationError

from .lib.jsonl import write_jsonl, append_jsonl, read_jsonl, index_jsonl_by
from .lib.fdc import load_foundation_foods_json, filter_nutrients_for_foods, load_nutrient_index
from .lib.llm import call_llm, DEFAULT_SYSTEM
from .db import GraphDB

MAPPING_SCHEMA = {
    "type": "object",
    "required": ["food_id", "name", "node_kind", "identity_json", "confidence", "rejected"],
    "properties": {
        "food_id": {"type":"string"},
        "name": {"type":"string"},
        "node_kind": {"enum":["taxon","tp","tpt"]},
        "node_id": {"type": ["string","null"]},
        "identity_json": {
            "type":"object",
            "required":["taxon_id","part_id","transforms"],
            "properties": {
                "taxon_id": {"type":"string"},
                "part_id": {"type":"string"},
                "transforms": {
                    "type":"array",
                    "items": {
                        "type":"object",
                        "required":["id"],
                        "properties": {
                            "id":{"type":"string"},
                            "params":{"type":["object","null"]}
                        }
                    }
                }
            }
        },
        "confidence":{"type":"number","minimum":0,"maximum":1},
        "rationales":{"type":"array","items":{"type":"string"}},
        "rejected":{"type":"boolean"},
        "new":{"type":"object"}
    },
    "additionalProperties": True
}

def _fmt_registry(parts: List[Dict[str,Any]], transforms: List[Dict[str,Any]]) -> str:
    def short_params(p):
        keys = []
        for item in (p or []):
            k = item.get("key"); kind = item.get("kind")
            if not k: continue
            keys.append(f"{k}:{kind}")
        return ", ".join(keys) if keys else "none"
    lines = ["# Parts (id → name/synonyms)"]
    for p in parts:
        syn = ", ".join(p.get("synonyms", [])[:4])
        lines.append(f"- {p['id']} → {p['name']}" + (f" (aka: {syn})" if syn else ""))
    lines.append("")
    lines.append("# Transforms (id → name; params)")
    for t in transforms:
        lines.append(f"- {t['id']} → {t['name']} ; params: {short_params(t.get('params'))}")
    return "\n".join(lines)

def _prompt(food: Dict[str,Any], candidates: List[Dict[str,Any]], registry_text: str) -> str:
    cand_lines = []
    for c in candidates[:5]:  # Limit to top 5 candidates to reduce tokens
        rid = c.get("ref_id"); nm = c.get("name"); rt = c.get("ref_type")
        pr = c.get("entity_rank"); fam = c.get("family") or ""
        cand_lines.append(f"- [{rt}] {rid} :: {nm} (rank={pr}{', family='+fam if fam else ''})")
    cand_block = "\n".join(cand_lines) or "(no candidates)"
    cat = food.get("category","")
    brand = food.get("brand","")
    return f"""Map FDC food to FoodState identity.

Food: {food.get('name','')} | {cat} | {brand}
Candidates: {cand_block}

Registry: {registry_text[:1000]}...

Rules:
- REJECT if this is a base food state (raw ingredient without processing)
- Only use provided registry IDs
- Prefer 'tp' over 'tpt' when uncertain about transforms
- Return null node_id if not certain

JSON: {{"node_kind":"tp","node_id":null,"identity_json":{{"taxon_id":"","part_id":"","transforms":[]}},"confidence":0.0,"rationales":[],"rejected":false}}"""

def main():
    ap = argparse.ArgumentParser(prog="evidence-map", description="Map FDC FOUNDATION foods to FoodState identity (JSONL only).")
    ap.add_argument("--graph", default="etl/build/database/graph.dev.sqlite", help="Path to graph database")
    ap.add_argument("--fdc", default="data/sources/fdc", help="Folder containing FDC data")
    ap.add_argument("--out", dest="out_dir", default="data/evidence/fdc-foundation")
    ap.add_argument("--model", default=os.environ.get("EVIDENCE_LLM_MODEL","gpt-4o-mini"))
    ap.add_argument("--min-conf", type=float, default=0.7)
    ap.add_argument("--topk", type=int, default=15)
    ap.add_argument("--limit", type=int, default=5, help="Limit number of foods processed (default: 5)")
    ap.add_argument("--overwrite", action="store_true", help="Rewrite mapping.jsonl instead of appending/resuming")
    args = ap.parse_args()

    start_time = time.time()
    
    # Find project root (where pnpm-workspace.yaml exists)
    project_root = Path(__file__).parent
    while project_root.parent != project_root:
        if (project_root / "pnpm-workspace.yaml").exists():
            break
        project_root = project_root.parent
    
    # Resolve all paths relative to project root
    out_dir = (project_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    foods_path = out_dir / "foods.jsonl"
    nutrients_path = out_dir / "nutrients.jsonl"
    mapping_path = out_dir / "mapping.jsonl"
    proposals_dir = out_dir / "_proposals"
    logs_dir = out_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Track timing and tokens
    timing_stats = {"total_time": 0, "per_food_times": [], "total_tokens": 0, "input_tokens": 0, "output_tokens": 0}
    
    log_file_path = logs_dir / "map.log"
    with log_file_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{datetime.utcnow().isoformat()}] run start model={args.model} min_conf={args.min_conf} topk={args.topk} limit={args.limit}\n")

    # 1) Load graph registries (parts, transforms) and prep candidate search
    # Resolve database path relative to project root
    if not Path(args.graph).is_absolute():
        db_path = (project_root / args.graph).resolve()
    else:
        db_path = Path(args.graph)
    gdb = GraphDB(str(db_path))
    parts = [ { "id": p.id, "name": p.name, "synonyms": p.synonyms } for p in gdb.parts() ]
    transforms = [ { "id": t.id, "name": t.name, "params": t.params } for t in gdb.transforms() ]
    registry_text = _fmt_registry(parts, transforms)

    # 2) Extract FDC → foods.jsonl (FOUNDATION only) + nutrients.jsonl restricted to those foods
    fdc_dir = (project_root / args.fdc).resolve()
    categories_skip = [  # tweak freely
        "mixed dishes", "fast foods", "baby foods", "snacks", "beverages", "soups, sauces, and gravies"
    ]
    foods = load_foundation_foods_json(fdc_dir, categories_skip=categories_skip, limit=args.limit)
    # Normalize and write foods.jsonl
    norm_foods: List[Dict[str, Any]] = []
    for r in foods:
        norm_foods.append({
            "food_id": f"fdc:{r.get('fdc_id')}",
            "fdc_id": r.get("fdc_id"),
            "name": r.get("description"),
            "brand": "",  # Not available in foundation-foods.json
            "data_type": "Foundation",
            "category_id": "",  # Not available in foundation-foods.json
            "category": r.get("category", ""),
            "lang": "en",
            "country": "US"
        })
    write_jsonl(foods_path, norm_foods)

    keep_ids = [r["fdc_id"] for r in foods if r.get("fdc_id")]
    fn_rows = filter_nutrients_for_foods(fdc_dir, keep_ids)
    nutrient_index = load_nutrient_index(fdc_dir)
    
    # Nutrient mapping from FDC to canonical IDs
    nutrient_map = {
        1008: "nutr:energy_kcal", 2047: "nutr:energy_kcal",
        1051: "nutr:water_g",
        1003: "nutr:protein_g",
        1004: "nutr:fat_g",
        1005: "nutr:carbohydrate_g",
        1079: "nutr:fiber_g",
        2000: "nutr:sugars_g", 1063: "nutr:sugars_g",
        1253: "nutr:cholesterol_mg",
        1258: "nutr:saturated_fat_g",
        1312: "nutr:monounsaturated_fat_g",
        1313: "nutr:polyunsaturated_fat_g",
        1093: "nutr:sodium_mg",
        1092: "nutr:potassium_mg",
        1087: "nutr:calcium_mg",
        1089: "nutr:iron_mg",
        1090: "nutr:magnesium_mg",
        1091: "nutr:phosphorus_mg",
        1095: "nutr:zinc_mg",
        1098: "nutr:copper_mg",
        1103: "nutr:selenium_mcg",
        1106: "nutr:vitamin_a_rae_mcg",
        1109: "nutr:vitamin_e_mg",
        1114: "nutr:vitamin_d_mcg",
        1162: "nutr:vitamin_c_mg",
        1165: "nutr:thiamin_mg",
        1166: "nutr:riboflavin_mg",
        1167: "nutr:niacin_mg",
        1170: "nutr:pantothenic_acid_mg",
        1175: "nutr:vitamin_b6_mg",
        1057: "nutr:caffeine_mg"
    }
    
    norm_nutrients: List[Dict[str, Any]] = []
    for r in fn_rows:
        fdc_nutr_id = int(r.get("nutrient_id", 0))
        canonical_id = nutrient_map.get(fdc_nutr_id)
        if not canonical_id:
            continue  # Skip unmapped nutrients
            
        nutr = nutrient_index.get(str(fdc_nutr_id), {})
        norm_nutrients.append({
            "food_id": f"fdc:{r.get('fdc_id')}",
            "fdc_nutrient_id": fdc_nutr_id,
            "canonical_nutrient_id": canonical_id,
            "nutrient_name": nutr.get("name") or nutr.get("description") or "",
            "unit": nutr.get("unit_name") or "",
            "value": r.get("amount"),
            "basis": "per_100g",
            "method": "FDC",
        })
    write_jsonl(nutrients_path, norm_nutrients)

    # 3) LLM mapping per food
    # Resume support
    existing = { row.get("food_id"): True for row in read_jsonl(mapping_path) or [] } if mapping_path.exists() and not args.overwrite else {}
    if args.overwrite and mapping_path.exists():
        mapping_path.unlink()
    processed = 0
    rejected_count = 0
    
    for food in norm_foods:
        fid = food["food_id"]
        if fid in existing:
            continue
            
        food_start = time.time()
        name = food.get("name","")
        cands = gdb.search_candidates(name, topk=args.topk)
        prompt = _prompt(food, cands, registry_text)
        
        try:
            # Call LLM with token tracking
            response = call_llm(model=args.model, system=DEFAULT_SYSTEM, user=prompt, max_retries=3, temperature=0.1)
            
            # Extract token usage if available
            if isinstance(response, dict) and '_token_usage' in response:
                usage = response['_token_usage']
                timing_stats["input_tokens"] += usage['prompt_tokens']
                timing_stats["output_tokens"] += usage['completion_tokens']
                timing_stats["total_tokens"] += usage['total_tokens']
                # Remove token usage from the response object
                del response['_token_usage']
            
            # Decorate with food_id/name
            obj = response
            obj["food_id"] = fid
            obj["name"] = name
            
            # Strict validation - fail on schema errors
            validate(instance=obj, schema=MAPPING_SCHEMA)
            
            # Track rejections
            if obj.get("rejected", False):
                rejected_count += 1
            
            append_jsonl(mapping_path, obj)
            
            # Optional: dump proposals for human triage
            new = obj.get("new") or {}
            if any(new.get(k) for k in ("taxa","parts","transforms")):
                proposals_dir.mkdir(parents=True, exist_ok=True)
                with (proposals_dir / f"{fid.replace(':','_')}.json").open("w", encoding="utf-8") as f:
                    json.dump({"food": food, "proposals": new}, f, ensure_ascii=False, indent=2)
            
            processed += 1
            food_time = time.time() - food_start
            timing_stats["per_food_times"].append(food_time)
            
            if processed % 5 == 0:
                with log_file_path.open("a", encoding="utf-8") as f:
                    f.write(f"  processed={processed} rejected={rejected_count} avg_time={sum(timing_stats['per_food_times'])/len(timing_stats['per_food_times']):.2f}s\n")
                
        except ValidationError as ve:
            with log_file_path.open("a", encoding="utf-8") as f:
                f.write(f"[VALIDATION_ERROR] {fid} {name}: {ve}\n")
            append_jsonl(mapping_path, {
                "food_id": fid, "name": name, "validation_error": str(ve)[:300], "node_kind": "tp",
                "node_id": None, "identity_json": {"taxon_id":"", "part_id":"", "transforms":[]},
                "confidence": 0.0, "rationales": ["Validation error"], "rejected": True
            })
            processed += 1
            rejected_count += 1
        except Exception as e:
            with log_file_path.open("a", encoding="utf-8") as f:
                f.write(f"[ERR] {fid} {name}: {e}\n")
            append_jsonl(mapping_path, {
                "food_id": fid, "name": name, "error": str(e), "node_kind": "tp",
                "node_id": None, "identity_json": {"taxon_id":"", "part_id":"", "transforms":[]},
                "confidence": 0.0, "rationales": ["LLM error"], "rejected": True
            })
            processed += 1
            rejected_count += 1
    
    # Final timing summary
    timing_stats["total_time"] = time.time() - start_time
    avg_time_per_food = sum(timing_stats["per_food_times"]) / len(timing_stats["per_food_times"]) if timing_stats["per_food_times"] else 0
    
    with log_file_path.open("a", encoding="utf-8") as f:
        f.write(f"[done] processed={processed} rejected={rejected_count} total_time={timing_stats['total_time']:.2f}s avg_per_food={avg_time_per_food:.2f}s\n")
        f.write(f"[tokens] input={timing_stats['input_tokens']} output={timing_stats['output_tokens']} total={timing_stats['total_tokens']}\n")
    
    # Print summary to console
    print(f"\n=== Evidence Mapping Complete ===")
    print(f"Processed: {processed} foods")
    print(f"Rejected: {rejected_count} foods")
    print(f"Total time: {timing_stats['total_time']:.2f}s")
    print(f"Avg per food: {avg_time_per_food:.2f}s")
    print(f"Tokens used: {timing_stats['total_tokens']} (input: {timing_stats['input_tokens']}, output: {timing_stats['output_tokens']})")
    print(f"Output: {out_dir}")

if __name__ == "__main__":
    main()
