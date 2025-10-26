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
You will receive a STATIC BLOCK followed by one ITEM per request.
Return STRICT JSON for that item only—no prose, no markdown, no extra keys.

Rules (critical):
- Prefer existing taxon_id from the graph; only emit new_taxa if none fits (with full contiguous parents).
- Follow the kingdom-specific ladders exactly; do not skip intermediate ranks.
- Hybrids: use x_ prefix in the species segment (e.g., x_ananassa).
- Only cultivar/variety are permitted in plant suffixes; animals may append [breed]. Otherwise, back off rank.
- Ignore marketing tokens (colors/grades/size) in taxon_id.
- Non-biological items (minerals/water) => disposition="skip" with null IDs.
- Processed meat products (frankfurters, sausages, hot dogs, deli meats) are typically multi-ingredient and should be disposition="skip".
- When in doubt about multi-ingredient status, prefer "skip" over forcing a single-species mapping.
- If label implies process (frozen, pasteurized, cooked, ground), you MUST include those transforms (if present in the registry) and set node_kind="tpt"; if missing, return disposition="ambiguous".
""".strip()

def call_llm(*, model: str, system: str, user: str = None, user_messages: List[str] = None, max_retries: int = 3, temperature: Optional[float] = None, client: OpenAI = None) -> Dict[str, Any]:
    if OpenAI is None:
        raise LLMError("openai SDK not installed. pip install openai>=1.0.0")
    
    # Validate input parameters
    if user is None and user_messages is None:
        raise ValueError("Either 'user' or 'user_messages' must be provided")
    if user is not None and user_messages is not None:
        raise ValueError("Cannot provide both 'user' and 'user_messages'")
    
    # Use provided client or create new one
    if client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise LLMError("OPENAI_API_KEY environment variable is required but not set. Please set it with your OpenAI API key.")
        client = OpenAI(api_key=api_key)
    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries+1):
        try:
            # Build messages list
            messages = [{"role": "system", "content": system or DEFAULT_SYSTEM}]
            
            if user is not None:
                # Single user message (backward compatibility)
                messages.append({"role": "user", "content": user})
            else:
                # Multiple user messages (new multi-message pattern)
                for user_msg in user_messages:
                    messages.append({"role": "user", "content": user_msg})
            
            create_args = {
                "model": model,
                "response_format": {"type": "json_object"},
                "messages": messages,
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
                usage = resp.usage
                token_usage = {
                    'prompt_tokens': getattr(usage, 'prompt_tokens', 0),
                    'completion_tokens': getattr(usage, 'completion_tokens', 0),
                    'total_tokens': getattr(usage, 'total_tokens', 0),
                }
                # Add cached tokens if available (for cached input optimization)
                cached = 0
                details = getattr(usage, "prompt_tokens_details", None)
                if isinstance(details, dict):
                    cached = details.get("cached_tokens", 0)
                elif details is not None:
                    cached = getattr(details, "cached_tokens", 0)
                token_usage['cached_tokens'] = cached
                result['_token_usage'] = token_usage
            
            return result
        except Exception as e:
            last_err = e
            time.sleep(0.5 * attempt + random.random() * 0.25)
    raise LLMError(f"LLM failed after {max_retries} attempts: {last_err}")
