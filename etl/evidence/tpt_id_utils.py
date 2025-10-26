#!/usr/bin/env python3
"""
TPT ID Generation Utilities

Shared utilities for generating canonical TPT IDs that match the ETL pipeline format.
"""

from __future__ import annotations
import hashlib
from typing import List, Dict, Any, Optional

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
    
    Filters to transforms with identity=true and includes all parameters.
    Sorts transforms and params for consistent hashing.
    """
    if not transforms:
        return "raw"
    
    # Load identity transforms from ontology
    identity_transform_ids = _get_identity_transform_ids()
    
    # Filter to identity transforms only
    identity_transforms = []
    for transform in transforms:
        tf_id = transform.get('id', '')
        if tf_id in identity_transform_ids:
            identity_transforms.append(transform)
    
    if not identity_transforms:
        return "raw"
    
    # Sort transforms by order (if available) then by id for consistency
    sorted_transforms = sorted(identity_transforms, key=lambda t: (t.get('order', 999), t.get('id', '')))
    
    # Create normalized signature
    signature_parts = []
    for transform in sorted_transforms:
        tf_id = transform.get('id', '')
        params = transform.get('params', {})
        
        # Sort params for consistent signature
        sorted_params = sorted(params.items()) if params else []
        param_str = ','.join(f"{k}={v}" for k, v in sorted_params)
        
        if param_str:
            signature_parts.append(f"{tf_id}({param_str})")
        else:
            signature_parts.append(tf_id)
    
    signature = '|'.join(signature_parts)
    
    # Create hash (first 12 chars of SHA1)
    hash_obj = hashlib.sha1(signature.encode('utf-8'))
    return hash_obj.hexdigest()[:12]

def _get_identity_transform_ids() -> set:
    """
    Load identity transform IDs from the ontology transforms.json file.
    
    Returns:
        Set of transform IDs that have identity=true
    """
    import json
    from pathlib import Path
    
    # Try to load from data/ontology/transforms.json
    transforms_file = Path("data/ontology/transforms.json")
    if not transforms_file.exists():
        # Fallback: return empty set if file doesn't exist
        return set()
    
    try:
        with open(transforms_file, 'r') as f:
            transforms_data = json.load(f)
        
        identity_ids = set()
        for transform in transforms_data:
            if transform.get('identity', False):
                identity_ids.add(transform.get('id', ''))
        
        return identity_ids
    except Exception:
        # Fallback: return empty set if there's an error
        return set()


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
