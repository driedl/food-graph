#!/usr/bin/env python3
"""
JSONL Utilities for Evidence Processing

Shared utilities for reading and processing JSONL files with consistent error handling.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Iterator, Optional
from .db_utils import log_stats

def read_jsonl_safe(file_path: Path, verbose: bool = False) -> Iterator[Dict[str, Any]]:
    """
    Safely read JSONL file with error handling and line tracking.
    
    Yields valid JSON objects, skips invalid lines with warnings.
    """
    if not file_path.exists():
        if verbose:
            print(f"  • File not found: {file_path}")
        return
    
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                yield json.loads(line.strip())
            except json.JSONDecodeError as e:
                if verbose:
                    print(f"  ⚠️  Invalid JSON on line {line_num}: {e}")
                continue
            except Exception as e:
                if verbose:
                    print(f"  ⚠️  Error processing line {line_num}: {e}")
                continue

def read_jsonl_list(file_path: Path, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Read entire JSONL file into a list with error handling.
    
    Returns list of valid JSON objects, logs errors for invalid lines.
    """
    return list(read_jsonl_safe(file_path, verbose))

def count_jsonl_lines(file_path: Path) -> int:
    """Count non-empty lines in JSONL file."""
    if not file_path.exists():
        return 0
    
    count = 0
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                count += 1
    return count

def validate_jsonl_schema(data: List[Dict[str, Any]], required_fields: List[str], 
                         file_name: str, verbose: bool = False) -> List[str]:
    """
    Validate JSONL data against required schema.
    
    Returns list of validation errors.
    """
    errors = []
    
    for i, item in enumerate(data):
        for field in required_fields:
            if field not in item:
                errors.append(f"{file_name}:{i+1}: missing required field '{field}'")
    
    if errors and verbose:
        print(f"  ⚠️  Schema validation errors in {file_name}:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"    - {error}")
        if len(errors) > 5:
            print(f"    - ... and {len(errors) - 5} more errors")
    
    return errors
