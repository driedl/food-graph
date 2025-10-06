from __future__ import annotations
import json, time, os, random
# Ensure .env is loaded once via centralized module (no-op if missing)
from .env import *  # noqa: F401,F403
from typing import Dict, Any, List, Optional
try:
    from openai import OpenAI
except Exception as e:
    OpenAI = None

class LLMError(Exception): ...

DEFAULT_SYSTEM = """
You convert FDC food records into a canonical FoodState for a nutrition graph.

DEFINITIONS (strict)
- Taxon ID: biological path starting with "tx:", e.g.
  tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos
- Part ID: edible/anatomical part starting with "part:"; MUST be in PART_REGISTRY.
- Transform ID: process starting with "tf:"; MUST be in TF_REGISTRY; include only identity-bearing params.
- Node kinds:
  - "taxon": only taxon known (no reliable part).
  - "tp": taxon + part known; transforms unknown/uncertain.
  - "tpt": taxon + part + ordered transforms (with params) known.

INPUT (per item)
{
  "label": "string",                    // e.g., "Hummus, commercial"
  "category": "string",                 // e.g., "Legumes and Legume Products"
  "registries": {
    "parts": ["part:...", "part:...", ...],  // Array of part IDs only
    "tf": ["tf:...", "tf:...", ...],         // Array of transform IDs only
    "tf_params": {                            // Allowed params per transform
      "tf:id": ["param_key", ...]
    }
  }
}

GLOBAL RULES
- Reject mixtures/processed foods: if label/category implies multi-ingredient, commercial processing, or prepared product (e.g., "hummus", "soup", "bar", "spread", "cereal", "mix", "frozen meal", "commercial"), then disposition="skip".
- Use only IDs from PART_REGISTRY and TF_REGISTRY. Never invent IDs. If something is truly missing, propose it under `new` as free text (no IDs).
- If transforms are uncertain, choose node_kind="tp" and set transforms=[].
- Prefer the most specific taxon you can justify; if species is uncertain, choose genus (lower confidence) or mark disposition="ambiguous" if even genus isn't safe.
- Order transforms logically (use provided transform.order if present; otherwise prep→cook→post).
- Include only identity-bearing params that are clearly implied; omit unknown values.

OUTPUT (STRICT JSON only; no prose, no markdown, no extra keys)
{
  "disposition": "map" | "skip" | "ambiguous",
  "node_kind": "taxon" | "tp" | "tpt",
  "identity_json": {
    "taxon_id": "tx:..." | null,
    "part_id": "part:..." | null,
    "transforms": [ { "id":"tf:...", "params": { /* only identity params */ } } ]
  },
  "confidence": 0.0-1.0,
  "reason_short": "≤20 words",
  "new": {
    "taxa":      [ { "name":"free text", "reason":"why it's needed" } ],
    "parts":     [ { "name":"free text", "reason":"why it's needed" } ],
    "transforms":[ { "name":"free text", "reason":"why it's needed" } ]
  }
}

HEURISTICS (compact)
- Fruits/vegetables: choose botanical part (fruit/leaf/root/seed/flower) consistent with label; raw state ⇒ "tp".
- Cereals/legumes (raw): seeds/grain parts; milling/pressing only if the label clearly implies it.
- Animal muscle cuts: taxon to genus/species if clear; part=muscle or specific cut if label indicates.
- Dairy: "yogurt/strained/greek" implies ferment (+ strain if explicit). Otherwise choose tp with milk.
- Do not map branded or composite names (sauces, dips, hummus, soups) → "skip".

MICRO-EXAMPLES
Input:
{"label":"Hummus, commercial","category":"Legumes and Legume Products","registries":{"parts":["part:fruit"],"tf":[],"tf_params":{}}}
Output:
{
  "disposition":"skip",
  "node_kind":"taxon",
  "identity_json":{"taxon_id":null,"part_id":null,"transforms":[]},
  "confidence":0.98,
  "reason_short":"processed mixture (policy: reject)",
  "new":{"taxa":[],"parts":[],"transforms":[]}
}

Input:
{"label":"Apple, raw","category":"Fruits and Fruit Juices","registries":{"parts":["part:fruit"],"tf":[],"tf_params":{}}}
Output:
{
  "disposition":"map",
  "node_kind":"tp",
  "identity_json":{
    "taxon_id":"tx:plantae:rosaceae:malus:domestica",
    "part_id":"part:fruit",
    "transforms":[]
  },
  "confidence":0.88,
  "reason_short":"raw edible fruit part",
  "new":{"taxa":[],"parts":[],"transforms":[]}
}
""".strip()

def call_llm(*, model: str, system: str, user: str, max_retries: int = 3, temperature: Optional[float] = None) -> Dict[str, Any]:
    if OpenAI is None:
        raise LLMError("openai SDK not installed. pip install openai>=1.0.0")
    
    # Check for OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY environment variable is required but not set. Please set it with your OpenAI API key.")
    
    client = OpenAI(api_key=api_key)
    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries+1):
        try:
            create_args = {
                "model": model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system or DEFAULT_SYSTEM},
                    {"role": "user", "content": user},
                ],
            }
            if temperature is not None:
                create_args["temperature"] = temperature
            resp = client.chat.completions.create(**create_args)
            content = resp.choices[0].message.content or "{}"
            result = json.loads(content)
            
            # Add token usage to result for tracking
            if hasattr(resp, 'usage') and resp.usage:
                result['_token_usage'] = {
                    'prompt_tokens': resp.usage.prompt_tokens,
                    'completion_tokens': resp.usage.completion_tokens,
                    'total_tokens': resp.usage.total_tokens
                }
            
            return result
        except Exception as e:
            last_err = e
            time.sleep(0.5 * attempt + random.random() * 0.25)
    raise LLMError(f"LLM failed after {max_retries} attempts: {last_err}")
