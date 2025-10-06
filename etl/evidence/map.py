from __future__ import annotations
import argparse, json, os, sys, re, time
# Ensure .env is loaded once via centralized module (no-op if missing)
from .lib.env import *  # type: ignore  # noqa: F401,F403
from pathlib import Path
from typing import Dict, Any, List, Iterable, Optional
from datetime import datetime
from jsonschema import validate, ValidationError

from .lib.jsonl import write_jsonl, append_jsonl, read_jsonl, index_jsonl_by
from .lib.fdc import load_foundation_foods_json, filter_nutrients_for_foods, load_nutrient_index, filter_base_foods
from .lib.llm import call_llm, DEFAULT_SYSTEM
from .db import GraphDB

MAPPING_SCHEMA = {
    "type": "object",
    "required": ["food_id", "name", "node_kind", "identity_json", "confidence", "disposition", "reason_short"],
    "properties": {
        "food_id": {"type":"string"},
        "name": {"type":"string"},
        "node_kind": {"enum":["taxon","tp","tpt"]},
        "node_id": {"type": ["string","null"]},
        "identity_json": {
            "type":"object",
            "required":["taxon_id","part_id","transforms"],
            "properties": {
                "taxon_id": {"type":["string","null"]},
                "part_id": {"type":["string","null"]},
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
        "disposition":{"enum":["map","skip","ambiguous"]},
        "reason_short":{"type":"string"},
        "rationales":{"type":"array","items":{"type":"string"}},
        "new_taxa":{"type":"array","items":{"type":"object"}},
        "new_parts":{"type":"array","items":{"type":"object"}},
        "new_transforms":{"type":"array","items":{"type":"object"}}
    },
    "additionalProperties": True
}


def _soft_validate_and_log(obj: Dict[str, Any], gdb: GraphDB, log_file_path: Path) -> None:
    """Soft validation: log missing taxa/parts/transforms but don't fail the mapping."""
    identity = obj.get("identity_json", {})
    fid = obj.get("food_id", "unknown")
    
    # Check taxon_id (with error handling for missing table)
    taxon_id = identity.get("taxon_id")
    if taxon_id:
        try:
            if not gdb.id_exists("nodes", "id", taxon_id):
                with log_file_path.open("a", encoding="utf-8") as f:
                    f.write(f"[MISSING_TAXON] {fid} | {taxon_id}\n")
        except Exception as e:
            with log_file_path.open("a", encoding="utf-8") as f:
                f.write(f"[VALIDATION_ERROR] {fid} | nodes table check failed: {e}\n")
    
    # Check part_id (with error handling for missing table)
    part_id = identity.get("part_id")
    if part_id:
        try:
            if not gdb.id_exists("part_def", "id", part_id):
                with log_file_path.open("a", encoding="utf-8") as f:
                    f.write(f"[MISSING_PART] {fid} | {part_id}\n")
        except Exception as e:
            with log_file_path.open("a", encoding="utf-8") as f:
                f.write(f"[VALIDATION_ERROR] {fid} | part_def table check failed: {e}\n")
    
    # Check transform IDs and params (with error handling for missing table)
    for transform in identity.get("transforms", []):
        tf_id = transform.get("id")
        if tf_id:
            try:
                if not gdb.id_exists("transform_def", "id", tf_id):
                    with log_file_path.open("a", encoding="utf-8") as f:
                        f.write(f"[MISSING_TRANSFORM] {fid} | {tf_id}\n")
            except Exception as e:
                with log_file_path.open("a", encoding="utf-8") as f:
                    f.write(f"[VALIDATION_ERROR] {fid} | transform_def table check failed: {e}\n")
        
        # Log unknown params (but don't fail)
        params = transform.get("params", {})
        if params:
            try:
                # Get allowed params for this transform
                allowed_params = set()
                for t in gdb.transforms():
                    if t.id == tf_id and t.params:
                        allowed_params.update(p.key for p in t.params if p.get("identity_param"))
                
                for param_key in params.keys():
                    if param_key not in allowed_params:
                        with log_file_path.open("a", encoding="utf-8") as f:
                            f.write(f"[UNKNOWN_PARAM] {fid} | {tf_id}.{param_key}\n")
            except Exception as e:
                with log_file_path.open("a", encoding="utf-8") as f:
                    f.write(f"[VALIDATION_ERROR] {fid} | param validation failed: {e}\n")

def _prompt(food: Dict[str,Any], parts: List[Dict[str,Any]], transforms: List[Dict[str,Any]]) -> str:
    # Token-lean registries: only IDs, and param key lists (no types/names)
    parts_ids = [p.get("id") for p in parts if p.get("id")]
    tf_compact = []
    for t in transforms:
        tf_compact.append({
            "id": t.get("id"),
            "param_keys": [p.get("key") for p in (t.get("params") or []) if p.get("key")]
        })
    input_data = {
        "label": food.get('name', ''),
        "category": food.get("category", ""),
        "registries": {
            "parts": parts_ids,
            "transforms": tf_compact
        }
    }
    
    return f"""Map this FDC food record to a canonical FoodState.

Input:
{json.dumps(input_data, separators=(',',':'))}

Output the JSON response as specified in the system prompt."""

def main():
    ap = argparse.ArgumentParser(prog="evidence-map", description="Map FDC FOUNDATION foods to FoodState identity (JSONL only).")
    ap.add_argument("--graph", default="etl/build/database/graph.dev.sqlite", help="Path to graph database")
    ap.add_argument("--fdc", default="data/sources/fdc", help="Folder containing FDC data")
    ap.add_argument("--out", dest="out_dir", default="data/evidence/fdc-foundation")
    ap.add_argument("--model", default=os.environ.get("EVIDENCE_LLM_MODEL","gpt-5-mini"))
    # Default temperature based on model (gpt-5-mini only supports 1.0)
    env_temperature = os.environ.get("EVIDENCE_LLM_TEMPERATURE")
    temperature: Optional[float] = 1.0  # Default for gpt-5-mini
    try:
        if env_temperature is not None:
            temperature = float(env_temperature)
    except Exception:
        temperature = 1.0
    
    ap.add_argument("--min-conf", type=float, default=0.7)
    ap.add_argument("--topk", type=int, default=15)
    ap.add_argument("--limit", type=int, default=5, help="Limit number of foods processed (default: 5)")
    ap.add_argument("--prompt-only", action="store_true", help="Generate and log the full prompt, then exit without calling LLM")
    ap.add_argument("--registry-limit", type=int, default=0, help="If >0, cap number of parts/transforms included in registries to reduce tokens")
    ap.add_argument("--include-derived", action="store_true", help="Include single-ingredient derivatives (oils, flours, salt/sugar, tahini).")
    ap.add_argument("--use-candidates", action="store_true", help="(Phase 2) inject search candidates; off by default.")
    ap.add_argument("--nutrient-registry", default="data/ontology/nutrients-infoods.json", help="Path to INFOODS registry.")
    ap.add_argument("--overwrite", action="store_true", help="Rewrite mapping.jsonl instead of appending/resuming")
    ap.add_argument("--debug-prompts", action="store_true", help="Save prompts and responses to debug directories")
    args = ap.parse_args()
    
    # Ensure gpt-5-mini uses temperature=1 (it only supports 1)
    if "gpt-5-mini" in args.model and temperature != 1.0:
        print(f"WARNING: gpt-5-mini only supports temperature=1, but got {temperature}. Setting to 1.")
        temperature = 1.0

    start_time = time.time()
    
    # Find project root (where pnpm-workspace.yaml exists)
    project_root = Path(__file__).parent
    while project_root.parent != project_root:
        if (project_root / "pnpm-workspace.yaml").exists():
            break
        project_root = project_root.parent
    
    # Fail fast if required API key is missing
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable is required but not set. Set it in your shell or .env.")
        sys.exit(1)

    # Resolve all paths relative to project root
    out_dir = (project_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    foods_path = out_dir / "foods.jsonl"
    nutrients_path = out_dir / "nutrients.jsonl"
    mapping_path = out_dir / "mapping.jsonl"
    proposals_dir = out_dir / "_proposals"
    logs_dir = out_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Debug directories for prompts and responses
    if args.debug_prompts:
        debug_prompts_dir = logs_dir / "prompts"
        debug_raw_dir = logs_dir / "raw"
        debug_bad_dir = logs_dir / "bad"
        debug_prompts_dir.mkdir(parents=True, exist_ok=True)
        debug_raw_dir.mkdir(parents=True, exist_ok=True)
        debug_bad_dir.mkdir(parents=True, exist_ok=True)
    
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
    def _min_part(p) -> Dict[str, Any]:
        obj = {"id": p.id}
        # Only include name if it adds information beyond id's last segment
        name = getattr(p, "name", None)
        last_seg = (p.id or "").split(":")[-1]
        if name and name.lower() != last_seg.replace("_"," "):
            obj["name"] = name
        syns = getattr(p, "synonyms", None) or []
        if syns:
            obj["synonyms"] = syns
        return obj
    parts = [ _min_part(p) for p in gdb.parts() ]
    def _only_identity_params(param_defs: Any) -> Any:
        out = []
        for pd in (param_defs or []):
            if pd.get("identity_param"):
                out.append({
                    "key": pd.get("key"),
                    "kind": pd.get("kind"),
                    "enum": pd.get("enum") if pd.get("enum") is not None else None,
                    "identity_param": True,
                })
        return out
    def _min_transform(t) -> Dict[str, Any]:
        obj: Dict[str, Any] = {"id": t.id}
        name = getattr(t, "name", None)
        if name:
            obj["name"] = name
        order_val = getattr(t, "order", None)
        if order_val is not None:
            obj["order"] = order_val
        params_val = _only_identity_params(getattr(t, "params", None))
        if params_val:
            obj["params"] = params_val
        return obj
    transforms = [ _min_transform(t) for t in gdb.transforms() ]
    if args.registry_limit and args.registry_limit > 0:
        parts = parts[:args.registry_limit]
        transforms = transforms[:args.registry_limit]

    # 2) Load existing foods.jsonl to create exclusion map for resume
    existing_foods = set()
    if foods_path.exists():
        for row in read_jsonl(foods_path) or []:
            existing_foods.add(row.get("food_id", ""))
    
    # 3) Extract FDC → foods.jsonl (FOUNDATION only) + nutrients.jsonl restricted to those foods
    fdc_dir = (project_root / args.fdc).resolve()
    # Normalize and expand category skip list
    categories_skip = [
        "mixed dishes", "fast foods", "baby foods", "snacks", "beverages", 
        "soups, sauces, and gravies", "restaurant foods", "sausages and luncheon meats",
        "baked products", "sweets", "fats and oils", "breakfast cereals",
        "cereal grains and pasta", "meals, entrees, and side dishes"
    ]
    # Normalize to lowercase for comparison
    categories_skip = [cat.lower() for cat in categories_skip]
    # Load all foundation foods (only ~400 total)
    foods_all = load_foundation_foods_json(fdc_dir, categories_skip=categories_skip, limit=None)
    foods = filter_base_foods(foods_all, include_derived=args.include_derived)
    # Normalize foods and filter out already processed ones, respecting limit for new foods
    norm_foods: List[Dict[str, Any]] = []
    for r in foods:
        fid = f"fdc:{r.get('fdc_id')}"
        if fid in existing_foods:
            continue  # Skip already processed
        if len(norm_foods) >= args.limit:
            break  # Stop when we have enough new foods to process
        norm_foods.append({
            "food_id": fid,
            "fdc_id": r.get("fdc_id"),
            "name": r.get("description"),
            "brand": "",  # Not available in foundation-foods.json
            "data_type": "Foundation",
            "category_id": "",  # Not available in foundation-foods.json
            "category": r.get("category", ""),
            "lang": "en",
            "country": "US"
        })

    keep_ids = [r["fdc_id"] for r in foods if r.get("fdc_id")]
    fn_rows = filter_nutrients_for_foods(fdc_dir, keep_ids)
    nutrient_index = load_nutrient_index(fdc_dir)
    
    # 3a) Load INFOODS registry mapping (fdc nutrient id -> INFOODS tag) and canonical units
    def _load_infoods_aliases(path: Path):
        import json
        fdc_to_tag: Dict[int, str] = {}
        tag_to_unit: Dict[str, str] = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            # Handle the specific structure of nutrients-infoods.json
            if isinstance(data, dict) and "nutrients" in data:
                nutrients = data["nutrients"]
                for it in nutrients:
                    tag = it.get("id")  # e.g., "PROCNT"
                    if not tag:
                        continue
                    unit = it.get("unit") or ""
                    if unit:
                        tag_to_unit[tag] = unit
                    # Look for FDC aliases in the aliases array
                    aliases = it.get("aliases", [])
                    if isinstance(aliases, list):
                        for alias in aliases:
                            # Check if this looks like an FDC nutrient ID (numeric)
                            try:
                                fdc_id = int(str(alias))
                                fdc_to_tag[fdc_id] = tag
                            except:
                                pass
            # Fallback for other structures
            elif isinstance(data, list):
                for it in data:
                    tag = it.get("nutrient_id") or it.get("id") or it.get("tag")
                    if not tag:
                        continue
                    unit = it.get("canonical_unit") or it.get("unit") or ""
                    if unit:
                        tag_to_unit[tag] = unit
                    # aliases: support shapes like {"aliases":{"fdc":["1003","1004"]}}
                    aliases = (it.get("aliases") or {})
                    fdc_alias = aliases.get("fdc") if isinstance(aliases, dict) else None
                    if isinstance(fdc_alias, list):
                        for a in fdc_alias:
                            try: fdc_to_tag[int(str(a))] = tag
                            except: pass
                    elif isinstance(fdc_alias, (str,int)):
                        try: fdc_to_tag[int(str(fdc_alias))] = tag
                        except: pass
            elif isinstance(data, dict):
                for tag, it in data.items():
                    if isinstance(it, dict):
                        unit = it.get("canonical_unit") or it.get("unit") or ""
                        if unit:
                            tag_to_unit[tag] = unit
                        aliases = it.get("aliases") or {}
                        fdc_alias = aliases.get("fdc")
                        if isinstance(fdc_alias, list):
                            for a in fdc_alias:
                                try: fdc_to_tag[int(str(a))] = tag
                                except: pass
                        elif isinstance(fdc_alias, (str,int)):
                            try: fdc_to_tag[int(str(fdc_alias))] = tag
                            except: pass
        return fdc_to_tag, tag_to_unit

    nr_path = (project_root / args.nutrient_registry).resolve()
    fdc_to_infoods, infoods_units = _load_infoods_aliases(nr_path)

    # fallback minimal map if registry lacks a code (kept tiny on purpose)
    _fallback = {1003:"PROCNT",1004:"FAT",1005:"CHOCDF",1008:"ENERC_KCAL",1051:"WATER",1079:"FIBTG",1093:"NA",1087:"CA"}
    
    # UCUM-ish unit normalization for simple FDC unit names
    _UNIT_MAP = {"G":"g","MG":"mg","UG":"µg","KCAL":"kcal","KJ":"kJ","IU":"IU"}
    norm_nutrients: List[Dict[str, Any]] = []
    for r in fn_rows:
        fdc_nutr_id = int(r.get("nutrient_id", 0))
        tag = fdc_to_infoods.get(fdc_nutr_id) or _fallback.get(fdc_nutr_id)
        if not tag:
            continue  # Skip unmapped nutrients
        nutr = nutrient_index.get(str(fdc_nutr_id), {})
        norm_nutrients.append({
            "food_id": f"fdc:{r.get('fdc_id')}",
            "fdc_nutrient_id": fdc_nutr_id,
            "nutrient_id": tag,  # INFOODS tag
            "nutrient_name": nutr.get("name") or nutr.get("description") or "",
            "unit": infoods_units.get(tag) or _UNIT_MAP.get((nutr.get("unit_name") or "").upper(), nutr.get("unit_name") or ""),
            "value": r.get("amount"),
            "basis": "per_100g",
            "method": "FDC",
        })
    write_jsonl(nutrients_path, norm_nutrients)

    # 4) LLM mapping per food (write foods.jsonl per item for sync)
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
        
        # Write food to foods.jsonl immediately for sync
        append_jsonl(foods_path, food)
        
        # Log food start
        with log_file_path.open("a", encoding="utf-8") as f:
            f.write(f"[FOOD] {fid} | {name}\n")
        print(f"[FOOD] {fid} | {name}")
        
        # Phase-2: cands optional
        if args.use_candidates:
            _ = gdb.search_candidates(name, topk=args.topk)  # not injected yet
        prompt = _prompt(food, parts, transforms)
        
        # Debug logging for prompts
        if args.debug_prompts:
            prompt_data = {
                "food_id": fid,
                "food_name": name,
                "system": DEFAULT_SYSTEM,
                "user_prompt": prompt
            }
            with (debug_prompts_dir / f"{fid.replace(':', '_')}.json").open("w", encoding="utf-8") as f:
                json.dump(prompt_data, f, ensure_ascii=False, indent=2)
        
        if args.prompt_only:
            from .lib.llm import DEFAULT_SYSTEM as SYS
            with log_file_path.open("a", encoding="utf-8") as f:
                f.write("\n=== SYSTEM INSTRUCTIONS BEGIN ===\n")
                f.write(SYS)
                f.write("\n=== SYSTEM INSTRUCTIONS END ===\n")
                f.write("\n--- PROMPT BEGIN ---\n")
                f.write(prompt)
                f.write("\n--- PROMPT END ---\n")
            processed += 1
            continue
        
        try:
            llm_start = time.time()
            # Call LLM with token tracking
            response = call_llm(model=args.model, system=DEFAULT_SYSTEM, user=prompt, max_retries=1, temperature=temperature)
            llm_time_ms = int((time.time() - llm_start) * 1000)
            
            # Extract token usage if available
            input_tokens = 0
            output_tokens = 0
            if isinstance(response, dict) and '_token_usage' in response:
                usage = response['_token_usage']
                input_tokens = usage['prompt_tokens']
                output_tokens = usage['completion_tokens']
                timing_stats["input_tokens"] += input_tokens
                timing_stats["output_tokens"] += output_tokens
                timing_stats["total_tokens"] += usage['total_tokens']
                # Remove token usage from the response object
                del response['_token_usage']
            
            # Debug logging for raw responses
            if args.debug_prompts:
                with (debug_raw_dir / f"{fid.replace(':', '_')}.json").open("w", encoding="utf-8") as f:
                    json.dump(response, f, ensure_ascii=False, indent=2)
            
            # Decorate with food_id/name
            obj = response
            obj["food_id"] = fid
            obj["name"] = name
            # normalize "new" fields to Phase-1 schema
            if "new" in obj and isinstance(obj.get("new"), dict):
                new = obj.pop("new") or {}
                obj.setdefault("new_taxa", new.get("taxa", []))
                obj.setdefault("new_parts", new.get("parts", []))
                obj.setdefault("new_transforms", new.get("transforms", []))
            
            # Strict validation - fail on schema errors
            try:
                validate(instance=obj, schema=MAPPING_SCHEMA)
            except ValidationError as ve:
                # Debug logging for validation errors
                if args.debug_prompts:
                    error_data = {
                        "food_id": fid,
                        "food_name": name,
                        "validation_error": str(ve),
                        "response": response
                    }
                    with (debug_bad_dir / f"{fid.replace(':', '_')}.json").open("w", encoding="utf-8") as f:
                        json.dump(error_data, f, ensure_ascii=False, indent=2)
                raise
            
            # Sort transforms by their order for consistency
            identity = obj.get("identity_json", {})
            transforms_list = identity.get("transforms", [])
            if transforms_list:
                # Create order map from transforms registry
                order_map = {t["id"]: t.get("order", 999) for t in transforms}
                transforms_list.sort(key=lambda x: order_map.get(x.get("id"), 999))
                identity["transforms"] = transforms_list
            
            # Soft validation - log missing ontology items but don't fail
            _soft_validate_and_log(obj, gdb, log_file_path)
            
            # Track rejections (now disposition-based)
            if obj.get("disposition") == "skip":
                rejected_count += 1
            
            append_jsonl(mapping_path, obj)
            
            # Optional: dump proposals for human triage
            new = obj.get("new") or {}
            if any(new.get(k) for k in ("taxa","parts","transforms")):
                proposals_dir.mkdir(parents=True, exist_ok=True)
                with (proposals_dir / f"{fid.replace(':','_')}.json").open("w", encoding="utf-8") as f:
                    json.dump({"food": food, "proposals": new}, f, ensure_ascii=False, indent=2)
            
            # Log per-food metrics
            food_time = time.time() - food_start
            with log_file_path.open("a", encoding="utf-8") as f:
                f.write(f"[METRICS] {fid} | llm={llm_time_ms}ms | tokens={input_tokens}+{output_tokens} | total={food_time:.1f}s\n")
            print(f"[METRICS] {fid} | llm={llm_time_ms}ms | tokens={input_tokens}+{output_tokens} | total={food_time:.1f}s")
            
            processed += 1
            timing_stats["per_food_times"].append(food_time)
            
            if processed % 5 == 0:
                avg_time = sum(timing_stats['per_food_times'])/len(timing_stats['per_food_times'])
                with log_file_path.open("a", encoding="utf-8") as f:
                    f.write(f"[BATCH] processed={processed} rejected={rejected_count} avg_time={avg_time:.2f}s\n")
                print(f"[BATCH] processed={processed} rejected={rejected_count} avg_time={avg_time:.2f}s")
                
        except ValidationError as ve:
            # Log only; do not persist error rows in mapping.jsonl
            with log_file_path.open("a", encoding="utf-8") as f:
                f.write(f"[VALIDATION_ERROR] {fid} | {name}: {ve}\n")
            print(f"[VALIDATION_ERROR] {fid} | {name}: {ve}")
            rejected_count += 1
        except Exception as e:
            # Log only; do not persist error rows in mapping.jsonl
            with log_file_path.open("a", encoding="utf-8") as f:
                f.write(f"[ERR] {fid} | {name}: {e}\n")
            print(f"[ERR] {fid} | {name}: {e}")
            rejected_count += 1
    
    # Final timing summary
    timing_stats["total_time"] = time.time() - start_time
    avg_time_per_food = sum(timing_stats["per_food_times"]) / len(timing_stats["per_food_times"]) if timing_stats["per_food_times"] else 0
    num_items = len(timing_stats["per_food_times"]) or 1
    avg_input_tokens = timing_stats["input_tokens"] / num_items
    avg_output_tokens = timing_stats["output_tokens"] / num_items
    
    with log_file_path.open("a", encoding="utf-8") as f:
        f.write(f"[done] processed={processed} rejected={rejected_count} total_time={timing_stats['total_time']:.2f}s avg_per_food={avg_time_per_food:.2f}s\n")
        f.write(f"[tokens] input={timing_stats['input_tokens']} output={timing_stats['output_tokens']} total={timing_stats['total_tokens']} avg_input={avg_input_tokens:.1f} avg_output={avg_output_tokens:.1f}\n")

    # Acceptance summary (Phase-1)
    accept = {
        "model": args.model,
        "processed": processed,
        "rejected": rejected_count,
        "yield_pct": (0 if processed==0 else round(100.0*(processed-rejected_count)/processed,1)),
        "total_time_s": round(timing_stats["total_time"],2),
        "avg_tokens_in": round(avg_input_tokens,1),
        "avg_tokens_out": round(avg_output_tokens,1),
        "include_derived": bool(args.include_derived)
    }
    with (logs_dir / "acceptance.json").open("w", encoding="utf-8") as f:
        json.dump(accept, f, ensure_ascii=False, indent=2)
    
    # Print summary to console
    print(f"\n=== Evidence Mapping Complete ===")
    print(f"Processed: {processed} foods")
    print(f"Rejected: {rejected_count} foods")
    print(f"Total time: {timing_stats['total_time']:.2f}s")
    print(f"Avg per food: {avg_time_per_food:.2f}s")
    print(f"Tokens used: {timing_stats['total_tokens']} (input: {timing_stats['input_tokens']}, output: {timing_stats['output_tokens']})")
    print(f"Avg tokens per item: input {avg_input_tokens:.1f}, output {avg_output_tokens:.1f}")
    print(f"Output: {out_dir}")

if __name__ == "__main__":
    main()
