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
    
    Format: tpt:{taxon_id}:{part_id}:{family}:{hash}
    Where hash is the first 12 characters of SHA1 of normalized transform signature.
    
    Args:
        taxon_id: Canonical taxon ID (e.g., "tx:a:bos:taurus")
        part_id: Canonical part ID (e.g., "part:milk")
        transforms: List of transform dictionaries with 'id' and 'params'
        family: Optional family name (defaults to "evidence" for evidence mappings)
    
    Returns:
        Canonical TPT ID string
    """
    if not taxon_id or not part_id:
        raise ValueError("taxon_id and part_id are required")
    
    # Use "evidence" as default family for evidence mappings
    if family is None:
        family = "evidence"
    
    # Generate transform signature (normalized)
    signature = _generate_transform_signature(transforms)
    
    # Create hash (first 12 chars of SHA1)
    hash_obj = hashlib.sha1(signature.encode('utf-8'))
    hash_suffix = hash_obj.hexdigest()[:12]
    
    return f"tpt:{taxon_id}:{part_id}:{family}:{hash_suffix}"

def _generate_transform_signature(transforms: List[Dict[str, Any]]) -> str:
    """
    Generate normalized signature for transform sequence.
    
    Sorts transforms by order/id and includes only identity parameters.
    """
    if not transforms:
        return "identity"
    
    # Sort transforms by order (if available) then by id
    sorted_transforms = sorted(transforms, key=lambda t: (t.get('order', 999), t.get('id', '')))
    
    signature_parts = []
    for transform in sorted_transforms:
        tf_id = transform.get('id', '')
        params = transform.get('params', {})
        
        # Only include identity parameters in signature
        identity_params = {k: v for k, v in params.items() 
                          if k in ['method', 'temperature', 'duration', 'level', 'type']}
        
        if identity_params:
            # Sort params for consistent signature
            sorted_params = sorted(identity_params.items())
            param_str = ','.join(f"{k}={v}" for k, v in sorted_params)
            signature_parts.append(f"{tf_id}({param_str})")
        else:
            signature_parts.append(tf_id)
    
    return '|'.join(signature_parts)

def validate_tpt_id_format(tpt_id: str) -> bool:
    """
    Validate that TPT ID follows canonical format.
    
    Args:
        tpt_id: TPT ID to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not tpt_id or not isinstance(tpt_id, str):
        return False
    
    parts = tpt_id.split(':')
    if len(parts) != 5:
        return False
    
    if parts[0] != 'tpt':
        return False
    
    # Check that hash part is 12 characters
    if len(parts[4]) != 12:
        return False
    
    return True
