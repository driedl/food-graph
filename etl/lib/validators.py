from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

def run_validators(spec: Dict[str, Any], build_dir: Path) -> List[str]:
    """Run all validators defined in a contract spec"""
    errs: List[str] = []
    for art in spec.get("artifacts", []):
        path = build_dir / art["path"]
        if art.get("must_exist", True) and not path.exists():
            errs.append(f"missing: {art['path']}")
            continue
        
        t = art.get("type", "jsonl")
        if t == "jsonl":
            lines = _read_jsonl(path)
            if "min_lines" in art and len(lines) < art["min_lines"]:
                errs.append(f"{art['path']}: min_lines {art['min_lines']} not met (got {len(lines)})")
            if "max_lines" in art and len(lines) > art["max_lines"]:
                errs.append(f"{art['path']}: max_lines {art['max_lines']} exceeded (got {len(lines)})")
            errs.extend(_apply_jsonl_validators(path, lines, art.get("validators", []), build_dir))
        elif t == "json":
            obj = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            errs.extend(_apply_json_validators(path, obj, art.get("validators", []), build_dir))
    return errs

def _read_jsonl(path: Path) -> List[dict]:
    """Read JSONL file, skipping empty lines and comments"""
    rows: List[dict] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("//"):
            continue
        try:
            rows.append(json.loads(s))
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{i}: invalid JSON: {e}")
    return rows

def _apply_jsonl_validators(path: Path, lines: List[dict], validators: List[Dict[str, Any]], build_dir: Path) -> List[str]:
    """Apply validators to JSONL data"""
    errs: List[str] = []
    for validator in validators:
        kind = validator.get("kind")
        if kind == "field_presence":
            errs.extend(_validate_field_presence(path, lines, validator))
        elif kind == "unique":
            errs.extend(_validate_unique(path, lines, validator))
        elif kind == "composite_unique":
            errs.extend(_validate_composite_unique(path, lines, validator))
        elif kind == "parent_exists":
            errs.extend(_validate_parent_exists(path, lines, validator))
        elif kind == "crossref_jsonl":
            errs.extend(_validate_crossref_jsonl(path, lines, validator, build_dir))
        elif kind == "crossref_json":
            errs.extend(_validate_crossref_json(path, lines, validator, build_dir))
        elif kind == "transform_ids_in":
            errs.extend(_validate_transform_ids_in(path, lines, validator, build_dir))
        elif kind == "transform_ids_in_objects":
            errs.extend(_validate_transform_ids_in_objects(path, lines, validator, build_dir))
        elif kind == "path_transform_ids_in":
            errs.extend(_validate_path_transform_ids_in(path, lines, validator, build_dir))
        elif kind == "no_duplicates":
            errs.extend(_validate_no_duplicates(path, lines, validator))
        elif kind == "hierarchy_consistency":
            errs.extend(_validate_hierarchy_consistency(path, lines, validator, build_dir))
        elif kind == "parameter_consistency":
            errs.extend(_validate_parameter_consistency(path, lines, validator, build_dir))
        elif kind == "schema_enum_compliance":
            errs.extend(_validate_schema_enum_compliance(path, lines, validator))
        elif kind == "id_format_consistency":
            errs.extend(_validate_id_format_consistency(path, lines, validator))
        elif kind == "required_fields_present":
            errs.extend(_validate_required_fields_present(path, lines, validator))
        elif kind == "cross_references_exist":
            errs.extend(_validate_cross_references_exist(path, lines, validator, build_dir))
        elif kind == "hierarchy_acyclic":
            errs.extend(_validate_hierarchy_acyclic(path, lines, validator))
        elif kind == "expected_parents":
            errs.extend(_validate_expected_parents(path, lines, validator))
        elif kind == "parameter_types_consistent":
            errs.extend(_validate_parameter_types_consistent(path, lines, validator))
        elif kind == "no_duplicate_definitions":
            errs.extend(_validate_no_duplicate_definitions(path, lines, validator))
        elif kind == "part_categories":
            errs.extend(_validate_part_categories(path, lines, validator))
        elif kind == "part_category_values":
            errs.extend(_validate_part_category_values(path, lines, validator))
        elif kind == "part_naming_convention":
            errs.extend(_validate_part_naming_convention(path, lines, validator))
        elif kind == "part_hierarchy_integrity":
            errs.extend(_validate_part_hierarchy_integrity(path, lines, validator, build_dir))
        else:
            errs.append(f"{path}: unknown validator kind: {kind}")

    return errs

def _apply_json_validators(path: Path, obj: Any, validators: List[Dict[str, Any]], build_dir: Path) -> List[str]:
    """Apply validators to JSON data"""
    errs: List[str] = []
    for validator in validators:
        kind = validator.get("kind")
        if kind == "array_of_objects":
            errs.extend(_validate_array_of_objects(path, obj, validator))
        elif kind == "set_nonempty":
            errs.extend(_validate_set_nonempty(path, obj, validator))
        elif kind == "json_pointer_equals":
            errs.extend(_validate_json_pointer_equals(path, obj, validator))
        elif kind == "no_duplicates":
            errs.extend(_validate_no_duplicates_json(path, obj, validator))
        elif kind == "hierarchy_consistency":
            errs.extend(_validate_hierarchy_consistency_json(path, obj, validator))
        elif kind == "schema_enum_compliance":
            errs.extend(_validate_schema_enum_compliance_json(path, obj, validator))
        elif kind == "id_format_consistency":
            errs.extend(_validate_id_format_consistency_json(path, obj, validator))
        elif kind == "required_fields_present":
            errs.extend(_validate_required_fields_present_json(path, obj, validator))
        elif kind == "cross_references_exist":
            errs.extend(_validate_cross_references_exist_json(path, obj, validator, build_dir))
        elif kind == "hierarchy_acyclic":
            errs.extend(_validate_hierarchy_acyclic_json(path, obj, validator))
        elif kind == "expected_parents":
            errs.extend(_validate_expected_parents_json(path, obj, validator))
        elif kind == "parameter_types_consistent":
            errs.extend(_validate_parameter_types_consistent_json(path, obj, validator))
        elif kind == "parameter_consistency":
            errs.extend(_validate_parameter_consistency_json(path, obj, validator, build_dir))
        elif kind == "no_duplicate_definitions":
            errs.extend(_validate_no_duplicate_definitions_json(path, obj, validator))
        else:
            errs.append(f"{path}: unknown validator kind: {kind}")

    return errs

# ============================================================================
# Core Validators
# ============================================================================

def _validate_field_presence(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate that required fields are present"""
    errs: List[str] = []
    fields = validator.get("fields", [])
    for i, line in enumerate(lines, 1):
        for field in fields:
            if field not in line:
                errs.append(f"{path}:{i}: missing field '{field}'")
    return errs

def _validate_unique(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate that field values are unique"""
    errs: List[str] = []
    field = validator.get("field", "id")
    seen: Set[Any] = set()
    for i, line in enumerate(lines, 1):
        value = line.get(field)
        if value in seen:
            errs.append(f"{path}:{i}: duplicate value for field '{field}': {value}")
        seen.add(value)
    return errs

def _validate_composite_unique(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate that composite keys are unique"""
    errs: List[str] = []
    fields = validator.get("fields", [])
    seen: Set[Tuple[Any, ...]] = set()
    for i, line in enumerate(lines, 1):
        key = tuple(line.get(field) for field in fields)
        if key in seen:
            errs.append(f"{path}:{i}: duplicate composite key: {dict(zip(fields, key))}")
        seen.add(key)
    return errs

def _validate_parent_exists(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate that parent references exist"""
    errs: List[str] = []
    id_field = validator.get("id_field", "id")
    parent_field = validator.get("parent_field", "parent")
    
    # Build ID set
    ids = {line.get(id_field) for line in lines if id_field in line}
    
    for i, line in enumerate(lines, 1):
        parent = line.get(parent_field)
        if parent and parent not in ids:
            errs.append(f"{path}:{i}: parent '{parent}' not found in {id_field} field")
    return errs

def _validate_crossref_jsonl(path: Path, lines: List[dict], validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """Validate that field values exist in another JSONL file"""
    errs: List[str] = []
    this_field = validator.get("this_field")
    other_path = build_dir / validator.get("other_path", "")
    other_field = validator.get("other_field", "id")
    
    if not this_field or not other_path.exists():
        return errs
    
    # Load reference data
    ref_data = _read_jsonl(other_path)
    ref_values = {line.get(other_field) for line in ref_data if other_field in line}
    
    for i, line in enumerate(lines, 1):
        value = line.get(this_field)
        if value and value not in ref_values:
            errs.append(f"{path}:{i}: {this_field} '{value}' not found in {other_path}")
    return errs

def _validate_crossref_json(path: Path, lines: List[dict], validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """Validate that field values exist in a JSON file"""
    errs: List[str] = []
    this_field = validator.get("this_field")
    other_path = build_dir / validator.get("other_path", "")
    other_field = validator.get("other_field", "id")
    
    if not this_field or not other_path.exists():
        return errs
    
    # Load reference data
    try:
        ref_data = json.loads(other_path.read_text(encoding="utf-8"))
        if isinstance(ref_data, list):
            ref_values = {item.get(other_field) for item in ref_data if isinstance(item, dict) and other_field in item}
        else:
            ref_values = set()
    except (json.JSONDecodeError, KeyError):
        return errs
    
    for i, line in enumerate(lines, 1):
        value = line.get(this_field)
        if value and value not in ref_values:
            errs.append(f"{path}:{i}: {this_field} '{value}' not found in {other_path}")
    return errs

def _validate_transform_ids_in(path: Path, lines: List[dict], validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """Validate that transform IDs exist in transforms_canon.json"""
    errs: List[str] = []
    transforms_path = build_dir / validator.get("transforms_path", "tmp/transforms_canon.json")
    field = validator.get("field", "transforms")
    
    if not transforms_path.exists():
        return errs
    
    # Load transform IDs
    try:
        transforms_data = json.loads(transforms_path.read_text(encoding="utf-8"))
        if isinstance(transforms_data, dict):
            transform_ids = set(transforms_data.keys())
        elif isinstance(transforms_data, list):
            transform_ids = {t.get("id") for t in transforms_data if isinstance(t, dict) and "id" in t}
        else:
            transform_ids = set()
    except (json.JSONDecodeError, KeyError):
        return errs
    
    for i, line in enumerate(lines, 1):
        transforms = line.get(field, [])
        if isinstance(transforms, list):
            for transform_id in transforms:
                if transform_id not in transform_ids:
                    errs.append(f"{path}:{i}: transform ID '{transform_id}' not found in {transforms_path}")
    return errs

def _validate_transform_ids_in_objects(path: Path, lines: List[dict], validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """
    Validate that a field is an array of objects each with 'id' that exists in transforms_canon.json
    validator:
      { kind: "transform_ids_in_objects", transforms_path: "tmp/transforms_canon.json", field: "identity" }
    """
    errs: List[str] = []
    transforms_path = build_dir / validator.get("transforms_path", "tmp/transforms_canon.json")
    field = validator.get("field", "identity")
    if not transforms_path.exists():
        return errs
    try:
        transforms_data = json.loads(transforms_path.read_text(encoding="utf-8"))
        if isinstance(transforms_data, dict):
            transform_ids = set(transforms_data.keys())
        elif isinstance(transforms_data, list):
            transform_ids = {t.get("id") for t in transforms_data if isinstance(t, dict) and "id" in t}
        else:
            transform_ids = set()
    except (json.JSONDecodeError, KeyError):
        return errs
    for i, line in enumerate(lines, 1):
        arr = line.get(field, [])
        if isinstance(arr, list):
            for obj in arr:
                if not isinstance(obj, dict): 
                    continue
                tf_id = obj.get("id")
                if tf_id and tf_id not in transform_ids:
                    errs.append(f"{path}:{i}: transform ID '{tf_id}' not found in {transforms_path}")
    return errs

def _validate_path_transform_ids_in(path: Path, lines: List[dict], validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """Validate that transform IDs in path objects exist in transforms_canon.json"""
    errs: List[str] = []
    transforms_path = build_dir / validator.get("transforms_path", "tmp/transforms_canon.json")
    field = validator.get("field", "path")
    
    if not transforms_path.exists():
        return errs
    
    # Load transform IDs
    try:
        transforms_data = json.loads(transforms_path.read_text(encoding="utf-8"))
        if isinstance(transforms_data, dict):
            transform_ids = set(transforms_data.keys())
        elif isinstance(transforms_data, list):
            transform_ids = {t.get("id") for t in transforms_data if isinstance(t, dict) and "id" in t}
        else:
            transform_ids = set()
    except (json.JSONDecodeError, KeyError):
        return errs
    
    for i, line in enumerate(lines, 1):
        path_obj = line.get(field, {})
        if isinstance(path_obj, dict):
            transforms = path_obj.get("transforms", [])
            if isinstance(transforms, list):
                for transform in transforms:
                    if isinstance(transform, dict):
                        tf_id = transform.get("id")
                        if tf_id and tf_id not in transform_ids:
                            errs.append(f"{path}:{i}: transform ID '{tf_id}' not found in {transforms_path}")
    return errs

def _validate_no_duplicates(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate no duplicate IDs in a field"""
    errs: List[str] = []
    field = validator.get("field", "id")
    seen: Set[Any] = set()
    for i, line in enumerate(lines, 1):
        value = line.get(field)
        if value in seen:
            errs.append(f"{path}:{i}: duplicate value for field '{field}': {value}")
        seen.add(value)
    return errs

def _validate_no_duplicates_json(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate no duplicate IDs in a field (JSON version)"""
    errs: List[str] = []
    field = validator.get("field", "id")
    if not field or not isinstance(obj, list):
        return errs
    
    seen: Set[Any] = set()
    for i, item in enumerate(obj):
        if isinstance(item, dict):
            value = item.get(field)
            if value in seen:
                errs.append(f"{path}:[{i}]: duplicate value for field '{field}': {value}")
            seen.add(value)
    return errs

def _validate_hierarchy_consistency(path: Path, lines: List[dict], validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """Validate parent-child relationships (JSONL version)"""
    errs: List[str] = []
    parent_field = validator.get("parent_field", "parent_id")
    child_field = validator.get("child_field", "id")
    
    # Build ID set
    ids = {line.get(child_field) for line in lines if child_field in line}
    
    for i, line in enumerate(lines, 1):
        parent = line.get(parent_field)
        if parent and parent not in ids:
            errs.append(f"{path}:{i}: parent '{parent}' not found in {child_field} field")
    return errs

def _validate_hierarchy_consistency_json(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate parent-child relationships (JSON version)"""
    errs: List[str] = []
    parent_field = validator.get("parent_field", "parent_id")
    child_field = validator.get("child_field", "id")
    
    if not isinstance(obj, list):
        return errs
    
    # Build ID set
    ids = {item.get(child_field) for item in obj if isinstance(item, dict) and child_field in item}
    
    for i, item in enumerate(obj):
        if isinstance(item, dict):
            parent = item.get(parent_field)
            if parent and parent not in ids:
                errs.append(f"{path}:[{i}]: parent '{parent}' not found in {child_field} field")
    return errs

def _validate_parameter_consistency(path: Path, lines: List[dict], validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """Validate parameter consistency across files"""
    errs: List[str] = []
    transform_file = validator.get("transform_file", "tmp/transforms_canon.json")
    family_file = validator.get("family_file", "compiled/families.json")
    param_field = validator.get("param_field", "identity_params")
    
    # Load transform parameters
    transforms_path = build_dir / transform_file
    if not transforms_path.exists():
        return errs
    
    try:
        transforms_data = json.loads(transforms_path.read_text(encoding="utf-8"))
        if isinstance(transforms_data, list):
            transform_params = {}
            for t in transforms_data:
                if isinstance(t, dict) and "id" in t:
                    transform_params[t["id"]] = {p.get("key") for p in t.get("params", []) if isinstance(p, dict)}
        else:
            return errs
    except (json.JSONDecodeError, KeyError):
        return errs
    
    # Load family parameters
    families_path = build_dir / family_file
    if not families_path.exists():
        return errs
    
    try:
        families_data = json.loads(families_path.read_text(encoding="utf-8"))
        if not isinstance(families_data, list):
            return errs
    except (json.JSONDecodeError, KeyError):
        return errs
    
    # Validate family parameters against transform parameters
    for i, family in enumerate(families_data, 1):
        if not isinstance(family, dict):
            continue
        
        family_params = family.get(param_field, [])
        if not isinstance(family_params, list):
            continue
        
        for param in family_params:
            if not isinstance(param, str):
                continue
            
            # Check if this parameter is used in any transform
            found = False
            for transform_id, params in transform_params.items():
                if param in params:
                    found = True
                    break
            
            if not found:
                errs.append(f"{path}:[{i}]: family parameter '{param}' not found in any transform")
    
    return errs

def _validate_schema_enum_compliance(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate that field values are in allowed enum values"""
    errs: List[str] = []
    field = validator.get("field", "kind")
    allowed_values = set(validator.get("allowed_values", []))
    
    for i, line in enumerate(lines, 1):
        value = line.get(field)
        if value and value not in allowed_values:
            errs.append(f"{path}:{i}: {field} '{value}' not in allowed values: {sorted(allowed_values)}")
    return errs

def _validate_schema_enum_compliance_json(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate that field values are in allowed enum values (JSON version)"""
    errs: List[str] = []
    field = validator.get("field", "kind")
    allowed_values = set(validator.get("allowed_values", []))
    
    if not isinstance(obj, list):
        return errs
    
    for i, item in enumerate(obj):
        if isinstance(item, dict):
            value = item.get(field)
            if value and value not in allowed_values:
                errs.append(f"{path}:[{i}]: {field} '{value}' not in allowed values: {sorted(allowed_values)}")
    return errs

def _validate_id_format_consistency(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate ID format consistency using regex patterns - no data maintenance needed
    
    Patterns based on Ontology Bible specifications (/docs/Ontology-bible.md section 1.1)
    """
    errs: List[str] = []
    
    # Define ID patterns programmatically based on Ontology Bible
    patterns = {
        "part": r"^part:[a-z0-9_]+(:[a-z0-9_]+)*$",
        "transform": r"^tf:[a-z0-9_]+$", 
        "taxon": r"^tx:[a-z0-9_]+(:[a-z0-9_]+)*$",
        "attribute": r"^attr:[a-z0-9_]+$"
    }
    
    for i, line in enumerate(lines, 1):
        for field, pattern in patterns.items():
            if field in line:
                value = line[field]
                if not re.match(pattern, value):
                    errs.append(f"{path}:{i}: {field} ID '{value}' doesn't match pattern {pattern}")
    
    return errs

def _validate_id_format_consistency_json(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate ID format consistency using regex patterns (JSON version)"""
    errs: List[str] = []
    
    # Define ID patterns programmatically based on Ontology Bible
    patterns = {
        "part": r"^part:[a-z0-9_]+(:[a-z0-9_]+)*$",
        "transform": r"^tf:[a-z0-9_]+$", 
        "taxon": r"^tx:[a-z0-9_]+(:[a-z0-9_]+)*$",
        "attribute": r"^attr:[a-z0-9_]+$"
    }
    
    if not isinstance(obj, list):
        return errs
    
    for i, item in enumerate(obj):
        if isinstance(item, dict):
            for field, pattern in patterns.items():
                if field in item:
                    value = item[field]
                    if not re.match(pattern, value):
                        errs.append(f"{path}:[{i}]: {field} ID '{value}' doesn't match pattern {pattern}")
    
    return errs

def _validate_required_fields_present(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate required fields are present based on file type"""
    errs: List[str] = []
    file_type = validator.get("file_type", "")
    
    # Define required fields by file type
    required_fields = {
        "taxa": ["id", "rank", "display_name", "latin_name"],
        "parts": ["id", "kind", "name"],
        "transforms": ["id", "name"],
        "attributes": ["id", "name"],
        "nutrients": ["id", "name"],
        "categories": ["id", "name"]
    }
    
    fields = required_fields.get(file_type, [])
    for i, line in enumerate(lines, 1):
        for field in fields:
            if field not in line:
                errs.append(f"{path}:{i}: missing required field '{field}' for {file_type}")
    return errs

def _validate_required_fields_present_json(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate required fields are present based on file type (JSON version)"""
    errs: List[str] = []
    file_type = validator.get("file_type", "")
    
    # Define required fields by file type
    required_fields = {
        "taxa": ["id", "rank", "display_name", "latin_name"],
        "parts": ["id", "kind", "name"],
        "transforms": ["id", "name"],
        "attributes": ["id", "name"],
        "nutrients": ["id", "name"],
        "categories": ["id", "name"]
    }
    
    if not isinstance(obj, list):
        return errs
    
    fields = required_fields.get(file_type, [])
    for i, item in enumerate(obj):
        if isinstance(item, dict):
            for field in fields:
                if field not in item:
                    errs.append(f"{path}:[{i}]: missing required field '{field}' for {file_type}")
    return errs

def _validate_cross_references_exist(path: Path, lines: List[dict], validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """Validate all referenced IDs exist in their respective files - no data maintenance"""
    errs: List[str] = []
    
    # Load all defined IDs from compiled files
    id_sources = {
        "part": "compiled/parts.json",
        "transform": "tmp/transforms_canon.json", 
        "taxon": "compiled/taxa.jsonl"
    }
    
    defined_ids = {}
    for ref_type, file_path in id_sources.items():
        ref_path = build_dir / file_path
        if ref_path.exists():
            try:
                if file_path.endswith('.jsonl'):
                    data = _read_jsonl(ref_path)
                else:
                    data = json.loads(ref_path.read_text(encoding="utf-8"))
                
                if isinstance(data, list):
                    defined_ids[ref_type] = {item.get("id") for item in data if isinstance(item, dict)}
                elif isinstance(data, dict):
                    defined_ids[ref_type] = set(data.keys())
            except:
                defined_ids[ref_type] = set()
    
    # Check references
    for i, line in enumerate(lines, 1):
        # Check part references
        for field in ["part", "part_id", "parts"]:
            if field in line:
                value = line[field]
                if isinstance(value, str) and value.startswith("part:"):
                    if value not in defined_ids.get("part", set()):
                        errs.append(f"{path}:{i}: part reference '{value}' not found in parts.json")
                elif isinstance(value, list):
                    for part in value:
                        if part.startswith("part:") and part not in defined_ids.get("part", set()):
                            errs.append(f"{path}:{i}: part reference '{part}' not found in parts.json")
        
        # Check transform references  
        for field in ["transform", "transform_id", "transforms"]:
            if field in line:
                value = line[field]
                if isinstance(value, str) and value.startswith("tf:"):
                    if value not in defined_ids.get("transform", set()):
                        errs.append(f"{path}:{i}: transform reference '{value}' not found in transforms.json")
                elif isinstance(value, list):
                    for transform in value:
                        if transform.startswith("tf:") and transform not in defined_ids.get("transform", set()):
                            errs.append(f"{path}:{i}: transform reference '{transform}' not found in transforms.json")
        
        # Check taxon references
        for field in ["taxon", "taxon_id", "taxa"]:
            if field in line:
                value = line[field]
                if isinstance(value, str) and value.startswith("tx:"):
                    if value not in defined_ids.get("taxon", set()):
                        errs.append(f"{path}:{i}: taxon reference '{value}' not found in taxa.jsonl")
                elif isinstance(value, list):
                    for taxon in value:
                        if taxon.startswith("tx:") and taxon not in defined_ids.get("taxon", set()):
                            errs.append(f"{path}:{i}: taxon reference '{taxon}' not found in taxa.jsonl")
    
    return errs

def _validate_cross_references_exist_json(path: Path, obj: Any, validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """Validate all referenced IDs exist in their respective files (JSON version)"""
    errs: List[str] = []
    
    if not isinstance(obj, list):
        return errs
    
    # Load all defined IDs from compiled files
    id_sources = {
        "part": "compiled/parts.json",
        "transform": "tmp/transforms_canon.json", 
        "taxon": "compiled/taxa.jsonl"
    }
    
    defined_ids = {}
    for ref_type, file_path in id_sources.items():
        ref_path = build_dir / file_path
        if ref_path.exists():
            try:
                if file_path.endswith('.jsonl'):
                    data = _read_jsonl(ref_path)
                else:
                    data = json.loads(ref_path.read_text(encoding="utf-8"))
                
                if isinstance(data, list):
                    defined_ids[ref_type] = {item.get("id") for item in data if isinstance(item, dict)}
                elif isinstance(data, dict):
                    defined_ids[ref_type] = set(data.keys())
            except:
                defined_ids[ref_type] = set()
    
    # Check references
    for i, item in enumerate(obj):
        if isinstance(item, dict):
            # Check part references
            for field in ["part", "part_id", "parts"]:
                if field in item:
                    value = item[field]
                    if isinstance(value, str) and value.startswith("part:"):
                        if value not in defined_ids.get("part", set()):
                            errs.append(f"{path}:[{i}]: part reference '{value}' not found in parts.json")
                    elif isinstance(value, list):
                        for part in value:
                            if part.startswith("part:") and part not in defined_ids.get("part", set()):
                                errs.append(f"{path}:[{i}]: part reference '{part}' not found in parts.json")
            
            # Check transform references  
            for field in ["transform", "transform_id", "transforms"]:
                if field in item:
                    value = item[field]
                    if isinstance(value, str) and value.startswith("tf:"):
                        if value not in defined_ids.get("transform", set()):
                            errs.append(f"{path}:[{i}]: transform reference '{value}' not found in transforms.json")
                    elif isinstance(value, list):
                        for transform in value:
                            if transform.startswith("tf:") and transform not in defined_ids.get("transform", set()):
                                errs.append(f"{path}:[{i}]: transform reference '{transform}' not found in transforms.json")
            
            # Check taxon references
            for field in ["taxon", "taxon_id", "taxa"]:
                if field in item:
                    value = item[field]
                    if isinstance(value, str) and value.startswith("tx:"):
                        if value not in defined_ids.get("taxon", set()):
                            errs.append(f"{path}:[{i}]: taxon reference '{value}' not found in taxa.jsonl")
                    elif isinstance(value, list):
                        for taxon in value:
                            if taxon.startswith("tx:") and taxon not in defined_ids.get("taxon", set()):
                                errs.append(f"{path}:[{i}]: taxon reference '{taxon}' not found in taxa.jsonl")
    
    return errs

# Additional validators for JSON objects
def _validate_array_of_objects(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate that object is an array of objects"""
    errs: List[str] = []
    if not isinstance(obj, list):
        errs.append(f"{path}: expected array, got {type(obj).__name__}")
    else:
        for i, item in enumerate(obj):
            if not isinstance(item, dict):
                errs.append(f"{path}:[{i}]: expected object, got {type(item).__name__}")
    return errs

def _validate_set_nonempty(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate that array is non-empty"""
    errs: List[str] = []
    if isinstance(obj, list) and len(obj) == 0:
        errs.append(f"{path}: array is empty")
    return errs

def _validate_json_pointer_equals(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate that JSON pointer equals expected value"""
    errs: List[str] = []
    pointer = validator.get("pointer", "")
    expected = validator.get("equals")
    
    if not pointer or expected is None:
        return errs
    
    # Simple JSON pointer implementation
    try:
        parts = pointer.lstrip("/").split("/")
        current = obj
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                current = None
                break
        
        if current != expected:
            errs.append(f"{path}: {pointer} = {current}, expected {expected}")
    except Exception as e:
        errs.append(f"{path}: JSON pointer error: {e}")
    
    return errs

def _validate_hierarchy_acyclic(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate that hierarchy is acyclic"""
    errs: List[str] = []
    id_field = validator.get("id_field", "id")
    parent_field = validator.get("parent_field", "parent")
    
    # Build parent map
    parent_map = {}
    for line in lines:
        child_id = line.get(id_field)
        parent_id = line.get(parent_field)
        if child_id and parent_id:
            parent_map[child_id] = parent_id
    
    # Check for cycles
    for line in lines:
        child_id = line.get(id_field)
        if not child_id:
            continue
        
        visited = set()
        current = child_id
        while current in parent_map:
            if current in visited:
                errs.append(f"{path}: cycle detected involving {current}")
                break
            visited.add(current)
            current = parent_map[current]
    
    return errs

def _validate_hierarchy_acyclic_json(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate that hierarchy is acyclic (JSON version)"""
    errs: List[str] = []
    id_field = validator.get("id_field", "id")
    parent_field = validator.get("parent_field", "parent")
    
    if not isinstance(obj, list):
        return errs
    
    # Build parent map
    parent_map = {}
    for item in obj:
        if isinstance(item, dict):
            child_id = item.get(id_field)
            parent_id = item.get(parent_field)
            if child_id and parent_id:
                parent_map[child_id] = parent_id
    
    # Check for cycles
    for item in obj:
        if isinstance(item, dict):
            child_id = item.get(id_field)
            if not child_id:
                continue
            
            visited = set()
            current = child_id
            while current in parent_map:
                if current in visited:
                    errs.append(f"{path}: cycle detected involving {current}")
                    break
                visited.add(current)
                current = parent_map[current]
    
    return errs

def _validate_expected_parents(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate expected parent relationships"""
    errs: List[str] = []
    id_field = validator.get("id_field", "id")
    parent_field = validator.get("parent_field", "parent")
    expected_parents = validator.get("expected_parents", {})
    
    for i, line in enumerate(lines, 1):
        child_id = line.get(id_field)
        parent_id = line.get(parent_field)
        
        if child_id in expected_parents:
            expected = expected_parents[child_id]
            if parent_id != expected:
                errs.append(f"{path}:{i}: {child_id} expected parent '{expected}', got '{parent_id}'")
    
    return errs

def _validate_expected_parents_json(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate expected parent relationships (JSON version)"""
    errs: List[str] = []
    id_field = validator.get("id_field", "id")
    parent_field = validator.get("parent_field", "parent")
    expected_parents = validator.get("expected_parents", {})
    
    if not isinstance(obj, list):
        return errs
    
    for i, item in enumerate(obj):
        if isinstance(item, dict):
            child_id = item.get(id_field)
            parent_id = item.get(parent_field)
            
            if child_id in expected_parents:
                expected = expected_parents[child_id]
                if parent_id != expected:
                    errs.append(f"{path}:[{i}]: {child_id} expected parent '{expected}', got '{parent_id}'")
    
    return errs

def _validate_parameter_types_consistent(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate parameter types are consistent"""
    errs: List[str] = []
    # This is a placeholder - would need specific implementation based on requirements
    return errs

def _validate_parameter_types_consistent_json(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate parameter types are consistent (JSON version)"""
    errs: List[str] = []
    # This is a placeholder - would need specific implementation based on requirements
    return errs

def _validate_parameter_consistency_json(path: Path, obj: Any, validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """Validate parameter consistency across files (JSON version)"""
    errs: List[str] = []
    # This is a placeholder - would need specific implementation based on requirements
    return errs

def _validate_no_duplicate_definitions(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate no duplicate definitions"""
    errs: List[str] = []
    # This is a placeholder - would need specific implementation based on requirements
    return errs

def _validate_no_duplicate_definitions_json(path: Path, obj: Any, validator: Dict[str, Any]) -> List[str]:
    """Validate no duplicate definitions (JSON version)"""
    errs: List[str] = []
    # This is a placeholder - would need specific implementation based on requirements
    return errs

def _validate_part_categories(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate part categories"""
    errs: List[str] = []
    # This is a placeholder - would need specific implementation based on requirements
    return errs

def _validate_part_category_values(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate part category values"""
    errs: List[str] = []
    # This is a placeholder - would need specific implementation based on requirements
    return errs

def _validate_part_naming_convention(path: Path, lines: List[dict], validator: Dict[str, Any]) -> List[str]:
    """Validate part naming convention"""
    errs: List[str] = []
    # This is a placeholder - would need specific implementation based on requirements
    return errs

def _validate_part_hierarchy_integrity(path: Path, lines: List[dict], validator: Dict[str, Any], build_dir: Path) -> List[str]:
    """Validate part hierarchy integrity"""
    errs: List[str] = []
    # This is a placeholder - would need specific implementation based on requirements
    return errs
