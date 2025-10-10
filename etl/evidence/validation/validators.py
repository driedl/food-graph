from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set

# Try absolute imports first, fall back to relative
try:
    from etl.lib.validators import _apply_jsonl_validators, _apply_json_validators, _read_jsonl
    from etl.evidence.validation.ontology_checker import OntologyChecker
except ImportError:
    # Fall back to relative imports when running from etl directory
    from lib.validators import _apply_jsonl_validators, _apply_json_validators, _read_jsonl
    from .ontology_checker import OntologyChecker


def _add_fdc_fields(structured_error: dict, line: dict, fdc_data: dict) -> None:
    """Add FDC fields to structured error if available"""
    food_id = line.get("food_id")
    if food_id and food_id in fdc_data:
        fdc_row = fdc_data[food_id]
        structured_error["fdc_category"] = fdc_row.get("category", "")
        structured_error["fdc_data_type"] = fdc_row.get("data_type", "")
        structured_error["fdc_brand"] = fdc_row.get("brand", "")
        structured_error["fdc_fdc_id"] = fdc_row.get("fdc_id", "")


def _validate_evidence_ontology_consistency(path: Path, lines: List[dict], validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """Validate that all referenced IDs in evidence mapping exist in compiled ontology"""
    errs: List[str] = []
    graph_db_path = validator.get("graph_db_path", "etl/build/database/graph.dev.sqlite")
    
    # Resolve graph database path
    if not Path(graph_db_path).is_absolute():
        graph_db_path = build_dir / graph_db_path
    
    if not Path(graph_db_path).exists():
        errs.append(f"Graph database not found: {graph_db_path}")
        return errs
    
    # Load FDC data for cross-reference
    fdc_data = {}
    try:
        from etl.lib.validators import _read_jsonl
        fdc_path = path.parent / "foods.jsonl"
        if fdc_path.exists():
            fdc_lines = _read_jsonl(fdc_path)
            fdc_data = {row.get("food_id"): row for row in fdc_lines}
    except Exception:
        pass  # Continue without FDC data if not available
    
    try:
        checker = OntologyChecker(str(graph_db_path))
        
        for i, line in enumerate(lines, 1):
            identity_json = line.get("identity_json", {})
            if not isinstance(identity_json, dict):
                continue
            
            # Validate the complete identity_json
            identity_errors = checker.validate_identity_json(identity_json)
            for error in identity_errors:
                # Create structured error with full mapping record
                structured_error = dict(line)
                structured_error["validation_error"] = error
                structured_error["line_number"] = i
                
                # Add FDC fields if available
                _add_fdc_fields(structured_error, line, fdc_data)
                errs.append(structured_error)
    
    except Exception as e:
        errs.append(f"{path}: ontology validation failed: {e}")
    
    return errs


def _validate_evidence_confidence_ranges(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate confidence scores are within expected ranges and correlate with disposition"""
    errs: List[str] = []
    
    # Load FDC data for cross-reference
    fdc_data = {}
    try:
        from etl.lib.validators import _read_jsonl
        fdc_path = path.parent / "foods.jsonl"
        if fdc_path.exists():
            fdc_lines = _read_jsonl(fdc_path)
            fdc_data = {row.get("food_id"): row for row in fdc_lines}
    except Exception:
        pass  # Continue without FDC data if not available
    
    for i, line in enumerate(lines, 1):
        confidence = line.get("confidence")
        disposition = line.get("disposition", "").lower()
        
        if confidence is None:
            structured_error = dict(line)
            structured_error["validation_error"] = "missing confidence field"
            structured_error["line_number"] = i
            _add_fdc_fields(structured_error, line, fdc_data)
            errs.append(structured_error)
            continue
        
        try:
            conf_val = float(confidence)
        except (ValueError, TypeError):
            structured_error = dict(line)
            structured_error["validation_error"] = f"confidence must be a number, got {type(confidence).__name__}"
            structured_error["line_number"] = i
            _add_fdc_fields(structured_error, line, fdc_data)
            errs.append(structured_error)
            continue
        
        # Check range
        if not (0.0 <= conf_val <= 1.0):
            structured_error = dict(line)
            structured_error["validation_error"] = f"confidence {conf_val} must be between 0.0 and 1.0"
            structured_error["line_number"] = i
            _add_fdc_fields(structured_error, line, fdc_data)
            errs.append(structured_error)
        
        # Check disposition logic
        if disposition == "skip" and conf_val > 0.5:
            structured_error = dict(line)
            structured_error["validation_error"] = f"skip disposition with high confidence {conf_val} seems suspicious"
            structured_error["line_number"] = i
            _add_fdc_fields(structured_error, line, fdc_data)
            errs.append(structured_error)
        elif disposition == "map" and conf_val < 0.3:
            structured_error = dict(line)
            structured_error["validation_error"] = f"map disposition with low confidence {conf_val} seems suspicious"
            structured_error["line_number"] = i
            _add_fdc_fields(structured_error, line, fdc_data)
            errs.append(structured_error)
    
    return errs


def _validate_evidence_disposition_logic(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate disposition logic consistency"""
    errs: List[str] = []
    
    for i, line in enumerate(lines, 1):
        disposition = line.get("disposition", "").lower()
        node_kind = line.get("node_kind", "")
        identity_json = line.get("identity_json", {})
        
        if disposition == "skip":
            # Skip items should have null taxon_id and part_id
            taxon_id = identity_json.get("taxon_id")
            part_id = identity_json.get("part_id")
            if taxon_id is not None:
                errs.append(f"{path}:{i}: skip disposition but taxon_id is not null: {taxon_id}")
            if part_id is not None:
                errs.append(f"{path}:{i}: skip disposition but part_id is not null: {part_id}")
        
        elif disposition == "map":
            # Map items should have valid identity_json
            if not isinstance(identity_json, dict):
                errs.append(f"{path}:{i}: map disposition but identity_json is not an object")
                continue
            
            taxon_id = identity_json.get("taxon_id")
            part_id = identity_json.get("part_id")
            transforms = identity_json.get("transforms", [])
            
            # Check node_kind consistency
            if node_kind == "taxon" and (part_id is not None or transforms):
                errs.append(f"{path}:{i}: node_kind 'taxon' but has part_id or transforms")
            elif node_kind == "tp" and transforms:
                errs.append(f"{path}:{i}: node_kind 'tp' but has transforms")
            elif node_kind == "tpt" and not transforms:
                errs.append(f"{path}:{i}: node_kind 'tpt' but no transforms")
        
        elif disposition == "ambiguous":
            # Ambiguous items should have some identity data but low confidence
            confidence = line.get("confidence", 0)
            if confidence > 0.7:
                errs.append(f"{path}:{i}: ambiguous disposition with high confidence {confidence}")
    
    return errs


def _validate_fdc_id_format(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate FDC ID format (numeric)"""
    errs: List[str] = []
    field = validator.get("field", "food_id")
    
    for i, line in enumerate(lines, 1):
        value = line.get(field)
        if not value:
            continue
        
        # Extract FDC ID from food_id (e.g., "fdc:321359" -> "321359")
        if isinstance(value, str) and value.startswith("fdc:"):
            fdc_id = value[4:]  # Remove "fdc:" prefix
            if not fdc_id.isdigit():
                errs.append(f"{path}:{i}: {field} '{value}' has non-numeric FDC ID")
        elif not str(value).isdigit():
            errs.append(f"{path}:{i}: {field} '{value}' is not a valid FDC ID")
    
    return errs


def _validate_nutrient_id_format(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate nutrient ID format (FDC nutrient IDs)"""
    errs: List[str] = []
    field = validator.get("field", "nutrient_id")
    
    for i, line in enumerate(lines, 1):
        value = line.get(field)
        if not value:
            continue
        
        # FDC nutrient IDs should be numeric
        if not str(value).isdigit():
            errs.append(f"{path}:{i}: {field} '{value}' is not a valid FDC nutrient ID")
    
    return errs


def _validate_evidence_mapping_schema(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate evidence mapping schema compliance"""
    errs: List[str] = []
    
    # Define the expected schema
    required_fields = {
        "food_id": str,
        "name": str,
        "node_kind": str,
        "identity_json": dict,
        "confidence": (int, float),
        "disposition": str,
        "reason_short": str
    }
    
    allowed_node_kinds = {"taxon", "tp", "tpt"}
    allowed_dispositions = {"map", "skip", "ambiguous"}
    
    for i, line in enumerate(lines, 1):
        # Check required fields
        for field, expected_type in required_fields.items():
            if field not in line:
                errs.append(f"{path}:{i}: missing required field '{field}'")
                continue
            
            value = line[field]
            if not isinstance(value, expected_type):
                errs.append(f"{path}:{i}: field '{field}' must be {expected_type.__name__}, got {type(value).__name__}")
        
        # Check enum values
        node_kind = line.get("node_kind")
        if node_kind and node_kind not in allowed_node_kinds:
            errs.append(f"{path}:{i}: node_kind '{node_kind}' not in {allowed_node_kinds}")
        
        disposition = line.get("disposition")
        if disposition and disposition not in allowed_dispositions:
            errs.append(f"{path}:{i}: disposition '{disposition}' not in {allowed_dispositions}")
        
        # Check identity_json structure
        identity_json = line.get("identity_json", {})
        if isinstance(identity_json, dict):
            required_identity_fields = {"taxon_id", "part_id", "transforms"}
            for field in required_identity_fields:
                if field not in identity_json:
                    errs.append(f"{path}:{i}: identity_json missing required field '{field}'")
            
            # Check transforms array
            transforms = identity_json.get("transforms", [])
            if not isinstance(transforms, list):
                errs.append(f"{path}:{i}: identity_json.transforms must be an array")
            else:
                for j, transform in enumerate(transforms):
                    if not isinstance(transform, dict):
                        errs.append(f"{path}:{i}: identity_json.transforms[{j}] must be an object")
                        continue
                    
                    if "id" not in transform:
                        errs.append(f"{path}:{i}: identity_json.transforms[{j}] missing 'id' field")
    
    return errs


# Register evidence-specific validators
def _validate_evidence_label_implied_transforms(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate that labels implying processes have appropriate transforms and node_kind"""
    errs: List[str] = []
    
    # Load transform registry to check available transforms
    transform_registry = set()
    try:
        from etl.lib.validators import _read_jsonl
        # Try to load from build directory first, then fallback
        transform_paths = [
            build_dir / "database" / "transform_def.jsonl",
            Path("etl/build/database/transform_def.jsonl"),
            Path("etl/database/transform_def.jsonl")
        ]
        for tf_path in transform_paths:
            if tf_path.exists():
                tf_lines = _read_jsonl(tf_path)
                transform_registry = {row.get("id") for row in tf_lines if row.get("id")}
                break
    except Exception:
        pass  # Continue without transform registry if not available
    
    # Keywords that imply processing
    process_keywords = {
        "frozen", "pasteurized", "pasteurised", "cooked", "roasted", "broiled", 
        "grilled", "baked", "ground", "minced", "dried", "dehydrated", "fermented",
        "cultured", "aged", "smoked", "cured", "pickled", "canned", "juiced"
    }
    
    for i, line in enumerate(lines, 1):
        name = line.get("name", "").lower()
        node_kind = line.get("node_kind", "")
        identity_json = line.get("identity_json", {})
        transforms = identity_json.get("transforms", [])
        
        # Check if name contains process keywords
        has_process_keyword = any(keyword in name for keyword in process_keywords)
        
        if has_process_keyword:
            # Should be TPT with transforms
            if node_kind != "tpt":
                structured_error = dict(line)
                structured_error["validation_error"] = f"Label implies processing but node_kind is '{node_kind}', should be 'tpt'"
                structured_error["line_number"] = i
                errs.append(structured_error)
            elif not transforms:
                structured_error = dict(line)
                structured_error["validation_error"] = "Label implies processing but no transforms specified"
                structured_error["line_number"] = i
                errs.append(structured_error)
            elif transform_registry:
                # Check if required transforms exist in registry
                missing_transforms = []
                for transform in transforms:
                    transform_id = transform.get("id")
                    if transform_id and transform_id not in transform_registry:
                        missing_transforms.append(transform_id)
                
                if missing_transforms:
                    structured_error = dict(line)
                    structured_error["validation_error"] = f"Transforms not found in registry: {', '.join(missing_transforms)}"
                    structured_error["line_number"] = i
                    errs.append(structured_error)
    
    return errs


def _apply_evidence_jsonl_validators(path: Path, lines: List[dict], validators: List[Dict[str, Any]], build_dir: Path) -> List[str]:
    """Apply evidence-specific validators to JSONL data"""
    errs: List[str] = []
    
    for validator in validators:
        kind = validator.get("kind")
        if kind == "evidence_ontology_consistency":
            errs.extend(_validate_evidence_ontology_consistency(path, lines, validator, build_dir))
        elif kind == "evidence_confidence_ranges":
            errs.extend(_validate_evidence_confidence_ranges(path, lines, validator))
        elif kind == "evidence_disposition_logic":
            errs.extend(_validate_evidence_disposition_logic(path, lines, validator))
        elif kind == "fdc_id_format":
            errs.extend(_validate_fdc_id_format(path, lines, validator))
        elif kind == "nutrient_id_format":
            errs.extend(_validate_nutrient_id_format(path, lines, validator))
        elif kind == "evidence_mapping_schema":
            errs.extend(_validate_evidence_mapping_schema(path, lines, validator))
        elif kind == "evidence_label_implied_transforms":
            errs.extend(_validate_evidence_label_implied_transforms(path, lines, validator))
        else:
            # Fall back to standard validators
            errs.extend(_apply_jsonl_validators(path, lines, [validator], build_dir))
    
    return errs


def _apply_evidence_json_validators(path: Path, obj: Any, validators: List[Dict[str, Any]], build_dir: Path) -> List[str]:
    """Apply evidence-specific validators to JSON data"""
    errs: List[str] = []
    
    for validator in validators:
        kind = validator.get("kind")
        if kind in ["evidence_ontology_consistency", "evidence_confidence_ranges", 
                   "evidence_disposition_logic", "fdc_id_format", "nutrient_id_format", 
                   "evidence_mapping_schema"]:
            # These validators are JSONL-specific, skip for JSON
            continue
        else:
            # Fall back to standard validators
            errs.extend(_apply_json_validators(path, obj, [validator], build_dir))
    
    return errs
