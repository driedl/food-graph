#!/usr/bin/env python3
"""
Schema Validator for Evidence Mapping

Validates that TPT constructions use valid parts, transforms, and parameters
according to the ontology schema. Rejects invalid mappings.
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Structured validation error for Tier 3 remediation"""
    transform_index: int
    transform_id: str
    error_type: str  # 'invalid_enum', 'unknown_param', 'type_mismatch', 'invalid_part'
    param_name: Optional[str] = None
    attempted_value: Any = None
    valid_values: Optional[List[Any]] = None
    schema_constraint: Optional[Dict[str, Any]] = None
    message: str = ""


@dataclass
class ValidationResult:
    """Result of schema validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    structured_errors: List[ValidationError] = None  # New field for structured errors


class SchemaValidator:
    """Validates evidence mappings against ontology schema"""
    
    def __init__(self, parts_index: Dict[str, Any], transforms_index: Dict[str, Any]):
        """
        Initialize validator with ontology schemas
        
        Args:
            parts_index: Dict of {part_id: part_definition}
            transforms_index: Dict of {transform_id: transform_definition}
        """
        self.parts_index = parts_index
        self.transforms_index = transforms_index
    
    def validate_mapping(self, taxon_id: Optional[str], part_id: Optional[str], 
                        transforms: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate a complete TPT construction
        
        Args:
            taxon_id: Taxon ID (not validated here, validated by NCBI)
            part_id: Part ID to validate
            transforms: List of transforms with params to validate
            
        Returns:
            ValidationResult with errors/warnings and structured errors
        """
        errors = []
        warnings = []
        structured_errors = []
        
        # Validate part exists
        if part_id:
            if part_id not in self.parts_index:
                errors.append(f"Invalid part_id: '{part_id}' not in ontology")
                structured_errors.append(ValidationError(
                    transform_index=-1,
                    transform_id="",
                    error_type='invalid_part',
                    attempted_value=part_id,
                    valid_values=list(self.parts_index.keys()),
                    message=f"Invalid part_id: '{part_id}' not in ontology"
                ))
        
        # Validate each transform
        for i, transform in enumerate(transforms):
            if not isinstance(transform, dict):
                errors.append(f"Transform {i}: expected dict, got {type(transform).__name__}")
                continue
                
            tf_id = transform.get('id')
            params = transform.get('params', {})
            
            if not tf_id:
                errors.append(f"Transform {i}: missing 'id' field")
                continue
            
            # Check transform exists
            if tf_id not in self.transforms_index:
                errors.append(f"Transform {i}: invalid transform_id '{tf_id}' not in ontology")
                structured_errors.append(ValidationError(
                    transform_index=i,
                    transform_id=tf_id or "",
                    error_type='invalid_transform',
                    attempted_value=tf_id,
                    valid_values=list(self.transforms_index.keys()),
                    message=f"Invalid transform_id '{tf_id}'"
                ))
                continue
            
            # Validate parameters
            tdef = self.transforms_index[tf_id]
            param_errors, param_structured_errors = self._validate_params(i, tf_id, params, tdef)
            errors.extend([f"Transform {i} ({tf_id}): {err}" for err in param_errors])
            structured_errors.extend(param_structured_errors)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            structured_errors=structured_errors
        )
    
    def _validate_params(self, transform_index: int, tf_id: str, params: Dict[str, Any], 
                        tdef: Dict[str, Any]) -> Tuple[List[str], List[ValidationError]]:
        """Validate transform parameters against schema and return both string and structured errors"""
        errors = []
        structured_errors = []
        
        # Build param schema lookup
        param_schema = {}
        for p in tdef.get('params', []):
            if isinstance(p, dict) and 'key' in p:
                param_schema[p['key']] = p
        
        # Validate each provided param
        for key, value in params.items():
            if key not in param_schema:
                msg = f"unknown parameter '{key}'"
                errors.append(msg)
                structured_errors.append(ValidationError(
                    transform_index=transform_index,
                    transform_id=tf_id,
                    error_type='unknown_param',
                    param_name=key,
                    attempted_value=value,
                    valid_values=list(param_schema.keys()),
                    schema_constraint=param_schema,
                    message=msg
                ))
                continue
            
            schema = param_schema[key]
            kind = schema.get('kind')
            
            # Validate enum values
            if kind == 'enum':
                valid_values = schema.get('enum', [])
                if value not in valid_values:
                    msg = f"param '{key}': invalid value '{value}'. Must be one of: {valid_values}"
                    errors.append(msg)
                    structured_errors.append(ValidationError(
                        transform_index=transform_index,
                        transform_id=tf_id,
                        error_type='invalid_enum',
                        param_name=key,
                        attempted_value=value,
                        valid_values=valid_values,
                        schema_constraint=schema,
                        message=msg
                    ))
            
            # Validate number types
            elif kind == 'number':
                if not isinstance(value, (int, float)):
                    msg = f"param '{key}': expected number, got {type(value).__name__}"
                    errors.append(msg)
                    structured_errors.append(ValidationError(
                        transform_index=transform_index,
                        transform_id=tf_id,
                        error_type='type_mismatch',
                        param_name=key,
                        attempted_value=value,
                        valid_values=None,
                        schema_constraint=schema,
                        message=msg
                    ))
        
        return errors, structured_errors


def validate_tpt_construction(tpt_construction: Any, 
                              parts_index: Dict[str, Any],
                              transforms_index: Dict[str, Any]) -> ValidationResult:
    """
    Convenience function to validate a TPT construction
    
    Args:
        tpt_construction: TPTConstruction object or dict with taxon_id, part_id, transforms
        parts_index: Dict of {part_id: part_definition}
        transforms_index: Dict of {transform_id: transform_definition}
        
    Returns:
        ValidationResult with is_valid, errors, and structured_errors
    """
    if not tpt_construction:
        return ValidationResult(valid=True, errors=[], warnings=[], structured_errors=[])
    
    # Extract fields from object or dict
    if hasattr(tpt_construction, 'taxon_id'):
        taxon_id = tpt_construction.taxon_id
        part_id = tpt_construction.part_id
        transforms = tpt_construction.transforms or []
    elif isinstance(tpt_construction, dict):
        taxon_id = tpt_construction.get('taxon_id')
        part_id = tpt_construction.get('part_id')
        transforms = tpt_construction.get('transforms', [])
    else:
        return ValidationResult(
            valid=False, 
            errors=["Invalid tpt_construction type"],
            warnings=[],
            structured_errors=[]
        )
    
    validator = SchemaValidator(parts_index, transforms_index)
    result = validator.validate_mapping(taxon_id, part_id, transforms)
    
    return result

