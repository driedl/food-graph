#!/usr/bin/env python3
"""
Shared Transform Utilities

Common utilities for transform and parameter handling across ETL and evidence mapping.
This module provides canonical implementations that match the ETL pipeline's logic.
"""

from __future__ import annotations
from typing import List, Dict, Any


def get_identity_param_keys(tdef: Dict[str, Any]) -> List[str]:
    """
    Extract parameter keys that have identity_param=true.
    
    This is the canonical implementation used by both ETL pipeline and evidence mapping.
    
    Args:
        tdef: Transform definition with params array
        
    Returns:
        List of parameter keys that are identity-bearing
    """
    keys = []
    for p in tdef.get("params", []) or []:
        if isinstance(p, dict) and p.get("identity_param"):
            keys.append(p.get("key"))
    return keys


def normalize_params(raw: Any) -> Dict[str, Any]:
    """
    Normalize step.params into a {key: value} dict.
    
    Accepts multiple input formats:
      - dict: {"nitrite_ppm": 120}
      - array of {"key","value"}: [{"key":"nitrite_ppm","value":120}]
      - array of single-pair dicts: [{"nitrite_ppm":120}]
    
    This is the canonical implementation used by both ETL pipeline and evidence mapping.
    
    Args:
        raw: Raw params in any supported format
        
    Returns:
        Normalized dict of {param_key: param_value}
    """
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}
    if isinstance(raw, list):
        out: Dict[str, Any] = {}
        for item in raw:
            if isinstance(item, dict):
                if "key" in item and "value" in item:
                    out[str(item["key"])] = item["value"]
                elif len(item) == 1:
                    k = next(iter(item.keys()))
                    out[str(k)] = item[k]
        return out
    return {}


def filter_identity_params(params: Dict[str, Any], tdef: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter params to only identity-bearing ones.
    
    This is the canonical implementation used by both ETL pipeline and evidence mapping.
    
    Args:
        params: Normalized params dict
        tdef: Transform definition with params schema
        
    Returns:
        Dict containing only identity params, sorted by key
    """
    identity_keys = get_identity_param_keys(tdef)
    if not identity_keys:
        return {}
    return {k: params.get(k) for k in sorted(identity_keys) if k in params}


def filter_to_identity_transforms(transforms: List[Dict[str, Any]], 
                                   tindex: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter transforms to only identity-bearing ones, sorted by canonical order.
    
    This is the canonical implementation used by both ETL pipeline and evidence mapping.
    
    Args:
        transforms: List of transform dicts with 'id' and 'params'
        tindex: Index of transform definitions keyed by transform ID
        
    Returns:
        List of identity transforms with normalized params, sorted by order
    """
    identity_transforms = []
    for transform in transforms:
        tf_id = transform.get('id', '')
        tdef = tindex.get(tf_id)
        if not tdef:
            continue
        if not tdef.get('identity', False):
            continue
        identity_transforms.append({
            'id': tf_id,
            'params': transform.get('params', {}),
            'order': tdef.get('order', 999)
        })
    
    if not identity_transforms:
        return []
    
    # Sort by canonical order
    identity_transforms.sort(key=lambda t: (t['order'], t['id']))
    return identity_transforms


def build_identity_payload(transforms: List[Dict[str, Any]], 
                          tindex: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build identity payload from transforms.
    
    Filters to identity transforms, normalizes params, filters to identity params,
    and sorts by canonical order.
    
    This is the canonical implementation used by both ETL pipeline and evidence mapping.
    
    Args:
        transforms: List of transform dicts with 'id' and 'params'
        tindex: Index of transform definitions keyed by transform ID
        
    Returns:
        List of dicts with 'id' and 'params' (identity params only)
    """
    identity_transforms = filter_to_identity_transforms(transforms, tindex)
    
    payload = []
    for transform in identity_transforms:
        tf_id = transform['id']
        tdef = tindex[tf_id]
        
        # Normalize and filter params
        params = normalize_params(transform['params'])
        filtered_params = filter_identity_params(params, tdef)
        
        payload.append({
            "id": tf_id,
            "params": filtered_params
        })
    
    return payload


def is_identity_transform(transform_id: str, tindex: Dict[str, Dict[str, Any]]) -> bool:
    """
    Check if a transform is identity-bearing.
    
    Args:
        transform_id: Transform ID to check
        tindex: Index of transform definitions
        
    Returns:
        True if transform has identity=true
    """
    tdef = tindex.get(transform_id)
    if not tdef:
        return False
    return bool(tdef.get('identity', False))

