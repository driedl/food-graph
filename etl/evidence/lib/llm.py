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
You map FDC food names to a canonical FoodState for a nutrition graph. Output STRICT JSON only.

RULES
- Reject mixtures/processed foods (e.g., hummus, sauces, soups, deli meats, breads, cookies): disposition="skip".
- Use ONLY allowed ids from registries: parts:[...] and transforms:[{id, param_keys[]}].
- If transforms are uncertain: node_kind="tp" and transforms=[].
- Prefer the most specific taxon you can justify; if uncertain, back off (lower confidence) or mark "ambiguous".
- Include ONLY identity-bearing params; omit unknowns.

INPUT
{"label":"...","category":"...","registries":{"parts":["part:..."],"transforms":[{"id":"tf:...","param_keys":["..."]}]}}

OUTPUT
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
  "new_taxa": [],
  "new_parts": [],
  "new_transforms": []
}

HEURISTICS
- Fruits/vegetables: choose botanical part; raw ⇒ "tp".
- Cereals/legumes (raw): seeds/grain; milling only if name implies it.
- Animal muscle cuts: part=muscle/cut if indicated.
- Dairy/yogurt/cheese/sauces/spreads: skip (processed) unless obviously plain milk (not in this pass).
- Do not map branded or composite names.

MICRO-EXAMPLES
Input:
{"label":"Hummus, commercial","category":"Legumes and Legume Products","registries":{"parts":[],"transforms":[]}}
Output:
{"disposition":"skip","node_kind":"taxon","identity_json":{"taxon_id":null,"part_id":null,"transforms":[]},"confidence":0.98,"reason_short":"processed mixture","new_taxa":[],"new_parts":[],"new_transforms":[]}

Input:
{"label":"Apple, raw","category":"Fruits and Fruit Juices","registries":{"parts":["part:fruit"],"transforms":[]}}
Output:
{"disposition":"map","node_kind":"tp","identity_json":{"taxon_id":"tx:plantae:rosaceae:malus:domestica","part_id":"part:fruit","transforms":[]},"confidence":0.88,"reason_short":"raw edible fruit","new_taxa":[],"new_parts":[],"new_transforms":[]}
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
            # gpt-5-mini only supports temperature=1
            if "gpt-5-mini" in (model or "").lower():
                create_args["temperature"] = 1.0
            elif temperature is not None:
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
