from __future__ import annotations
import json, time, os, random
from typing import Dict, Any, List, Optional
try:
    from openai import OpenAI
except Exception as e:
    OpenAI = None

class LLMError(Exception): ...

DEFAULT_SYSTEM = """
You turn food labels/names into a canonical FoodState mapping for a nutrition graph.
FoodState identity format:
  - node_kind: 'taxon' | 'tp' | 'tpt' (prefer 'tp' if you can pick part but not transforms)
  - identity_json:
      { "taxon_id": "tx:...",
        "part_id": "part:...",
        "transforms": [ { "id": "tf:...", "params": {{...}} }, ... ] }
  - node_id: existing canonical id if known; else null
  - confidence: 0..1
  - new: optionally propose new {taxa[], parts[], transforms[]} when truly missing

Rules:
  - Only propose transforms from the provided registry.
  - Only propose parts from the provided registry.
  - If you cannot determine transforms with confidence, choose node_kind='tp' and leave transforms=[].
  - Never invent IDs outside registries; for new proposals, use free-text names and rationale only.
  - Output STRICT JSON only.
""".strip()

def call_llm(*, model: str, system: str, user: str, max_retries: int = 3, temperature: float = 0.1) -> Dict[str, Any]:
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
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                response_format={ "type": "json_object" },
                messages=[
                    { "role": "system", "content": system or DEFAULT_SYSTEM },
                    { "role": "user", "content": user },
                ],
            )
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
