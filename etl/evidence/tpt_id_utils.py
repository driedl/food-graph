#!/usr/bin/env python3
"""
TPT ID Generation Utilities

Shared utilities for generating canonical TPT IDs that match the ETL pipeline format.
Uses the same logic as etl/graph/stages/stage_e/canon_ids.py for consistency.
"""

from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import shared utilities
from lib.transform_utils import build_identity_payload

# Cache for loaded data to avoid repeated file I/O
_TRANSFORM_INDEX: Optional[Dict[str, Dict[str, Any]]] = None
_PARAM_BUCKETS: Optional[Dict[str, Dict[str, Any]]] = None

def generate_tpt_id(taxon_id: str, part_id: str, transforms: List[Dict[str, Any]], 
                   family: Optional[str] = None) -> str:
    """
    Generate canonical TPT ID matching the ETL pipeline format.
    
    Format: {taxon_id}|{part_id}|{identity_hash}
    Where identity_hash is the first 12 characters of SHA1 of normalized identity transforms.
    
    Args:
        taxon_id: Canonical taxon ID (e.g., "tx:a:bos:taurus")
        part_id: Canonical part ID (e.g., "part:milk")
        transforms: List of transform dictionaries with 'id' and 'params'
        family: Ignored (kept for compatibility)
    
    Returns:
        Canonical TPT ID string
    """
    if not taxon_id or not part_id:
        raise ValueError("taxon_id and part_id are required")
    
    # Generate identity hash from identity transforms only
    identity_hash = _generate_identity_hash(transforms)
    
    return f"{taxon_id}|{part_id}|{identity_hash}"

def _generate_identity_hash(transforms: List[Dict[str, Any]]) -> str:
    """
    Generate hash from identity transforms only.
    
    Matches ETL pipeline logic: filters to transforms with identity=true and 
    includes ONLY parameters with identity_param=true.
    """
    if not transforms:
        return "raw"
    
    # Load transform definitions (not just IDs, we need param schemas)
    tindex = _get_transform_index()
    if not tindex:
        print("WARNING: Failed to load transform definitions, cannot generate TPT ID hash", file=sys.stderr)
        return "raw"
    
    # Build identity payload using shared utility
    identity_payload = build_identity_payload(transforms, tindex)
    
    if not identity_payload:
        return "raw"
    
    # Apply param bucketing for consistent hashing
    buckets = _get_param_buckets()
    for step in identity_payload:
        for k in list(step["params"].keys()):
            pk = f'{step["id"]}.{k}'
            step["params"][k] = _bucket_value(pk, step["params"][k], buckets)
    
    # Generate signature using same format as ETL pipeline
    blob = json.dumps(
        {"steps": identity_payload},
        separators=(",", ":"), 
        sort_keys=True
    )
    
    # Create hash (first 12 chars of SHA1)
    hash_obj = hashlib.sha1(blob.encode('utf-8'))
    return hash_obj.hexdigest()[:12]

# Note: _build_identity_payload, _get_identity_param_keys, and _normalize_params
# are now provided by lib.transform_utils to avoid code duplication

def _bucket_value(key: str, val: Any, buckets: Dict[str, Dict[str, Any]]) -> Any:
    """
    Apply param bucketing for consistent hashing.
    Matches ETL pipeline's _bucket_value() logic.
    """
    cfg = buckets.get(key)
    if not cfg:
        return val
    cuts = cfg.get("cuts") or []
    labels = cfg.get("labels") or []
    if not isinstance(val, (int, float)) or not cuts or not labels:
        return val
    for i, cut in enumerate(cuts):
        try:
            if val <= float(cut):
                return labels[i] if i < len(labels) else val
        except Exception:
            return val
    return labels[-1] if labels else val

def _get_transform_index() -> Dict[str, Dict[str, Any]]:
    """
    Load and cache transform definitions from ontology.
    Returns dict keyed by transform ID with full definitions.
    """
    global _TRANSFORM_INDEX
    
    if _TRANSFORM_INDEX is not None:
        return _TRANSFORM_INDEX
    
    try:
        from lib.config import find_project_root, resolve_path
        
        project_root = find_project_root()
        transforms_file = resolve_path("data/ontology/transforms.json", project_root)
        
        if not transforms_file.exists():
            print(f"WARNING: transforms.json not found at {transforms_file}", file=sys.stderr)
            _TRANSFORM_INDEX = {}
            return _TRANSFORM_INDEX
        
        with open(transforms_file, 'r') as f:
            transforms_data = json.load(f)
        
        if not isinstance(transforms_data, list):
            print(f"WARNING: transforms.json must be a list, got {type(transforms_data)}", file=sys.stderr)
            _TRANSFORM_INDEX = {}
            return _TRANSFORM_INDEX
        
        # Index by transform ID
        _TRANSFORM_INDEX = {
            t["id"]: t for t in transforms_data 
            if isinstance(t, dict) and "id" in t
        }
        
        return _TRANSFORM_INDEX
        
    except Exception as e:
        print(f"WARNING: Error loading transforms.json: {e}", file=sys.stderr)
        _TRANSFORM_INDEX = {}
        return _TRANSFORM_INDEX

def _get_param_buckets() -> Dict[str, Dict[str, Any]]:
    """
    Load and cache param bucketing rules from ontology.
    Returns dict keyed by "transform_id.param_key" with bucket config.
    """
    global _PARAM_BUCKETS
    
    if _PARAM_BUCKETS is not None:
        return _PARAM_BUCKETS
    
    try:
        from lib.config import find_project_root, resolve_path
        
        project_root = find_project_root()
        buckets_file = resolve_path("data/ontology/rules/param_buckets.json", project_root)
        
        if not buckets_file.exists():
            # This is optional, so don't warn
            _PARAM_BUCKETS = {}
            return _PARAM_BUCKETS
        
        with open(buckets_file, 'r') as f:
            bucket_data = json.load(f)
        
        if not isinstance(bucket_data, dict):
            _PARAM_BUCKETS = {}
            return _PARAM_BUCKETS
        
        _PARAM_BUCKETS = bucket_data
        return _PARAM_BUCKETS
        
    except Exception:
        # Bucketing is optional
        _PARAM_BUCKETS = {}
        return _PARAM_BUCKETS


def validate_tpt_id_format(tpt_id: str) -> bool:
    """
    Validate that TPT ID follows canonical format.
    
    Format: {taxon_id}|{part_id}|{identity_hash}
    
    Args:
        tpt_id: TPT ID to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not tpt_id or not isinstance(tpt_id, str):
        return False
    
    parts = tpt_id.split('|')
    if len(parts) != 3:
        return False
    
    # Check that identity hash part is 12 characters or "raw"
    if parts[2] not in ["raw"] and len(parts[2]) != 12:
        return False
    
    return True
