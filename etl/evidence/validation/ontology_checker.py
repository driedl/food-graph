from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Set
import json

# Try absolute imports first, fall back to relative
try:
    from etl.evidence.db import GraphDB
except ImportError:
    # Fall back to relative imports when running from etl directory
    from evidence.db import GraphDB


class OntologyChecker:
    """Database-backed ontology validation for evidence files"""
    
    def __init__(self, graph_db_path: str):
        """Initialize with path to compiled graph database"""
        self.gdb = GraphDB(graph_db_path)
        self._taxon_ids: Set[str] = set()
        self._part_ids: Set[str] = set()
        self._transform_ids: Set[str] = set()
        self._transform_params: Dict[str, Set[str]] = {}
        self._loaded = False
    
    def _ensure_loaded(self) -> None:
        """Lazy load all ontology IDs for efficient validation"""
        if self._loaded:
            return
        
        # Load taxon IDs
        try:
            for taxon in self.gdb.con.execute("SELECT id FROM nodes WHERE id LIKE 'tx:%'"):
                self._taxon_ids.add(taxon["id"])
        except Exception:
            pass  # Table might not exist yet
        
        # Load part IDs
        try:
            for part in self.gdb.con.execute("SELECT id FROM part_def"):
                self._part_ids.add(part["id"])
        except Exception:
            pass  # Table might not exist yet
        
        # Load transform IDs and parameters
        try:
            for transform in self.gdb.con.execute("SELECT id, param_keys FROM transform_def"):
                self._transform_ids.add(transform["id"])
                try:
                    params = json.loads(transform["param_keys"] or "[]")
                    if isinstance(params, list):
                        param_keys = set()
                        for param in params:
                            if isinstance(param, dict) and "key" in param:
                                param_keys.add(param["key"])
                        self._transform_params[transform["id"]] = param_keys
                except Exception:
                    pass
        except Exception:
            pass  # Table might not exist yet
        
        self._loaded = True
    
    def validate_taxon_exists(self, taxon_id: str) -> bool:
        """Check if taxon ID exists in compiled ontology"""
        if not taxon_id or not taxon_id.startswith("tx:"):
            return False
        
        self._ensure_loaded()
        return taxon_id in self._taxon_ids
    
    def validate_part_exists(self, part_id: str) -> bool:
        """Check if part ID exists in compiled ontology"""
        if not part_id or not part_id.startswith("part:"):
            return False
        
        self._ensure_loaded()
        return part_id in self._part_ids
    
    def validate_transform_exists(self, transform_id: str) -> bool:
        """Check if transform ID exists in compiled ontology"""
        if not transform_id or not transform_id.startswith("tf:"):
            return False
        
        self._ensure_loaded()
        return transform_id in self._transform_ids
    
    def validate_transform_params(self, transform_id: str, params: Dict[str, Any]) -> List[str]:
        """Validate transform parameters against transform definition"""
        if not transform_id or not params:
            return []
        
        self._ensure_loaded()
        
        if transform_id not in self._transform_ids:
            return [f"Transform '{transform_id}' not found in ontology"]
        
        allowed_params = self._transform_params.get(transform_id, set())
        if not allowed_params:
            return []  # No parameter validation if no param definition
        
        errors = []
        for param_key in params.keys():
            if param_key not in allowed_params:
                errors.append(f"Unknown parameter '{param_key}' for transform '{transform_id}'")
        
        return errors
    
    def validate_identity_json(self, identity_json: Dict[str, Any]) -> List[str]:
        """Validate a complete identity_json object"""
        errors = []
        
        if not isinstance(identity_json, dict):
            return ["identity_json must be an object"]
        
        # Validate taxon_id
        taxon_id = identity_json.get("taxon_id")
        if taxon_id and not self.validate_taxon_exists(taxon_id):
            errors.append(f"Taxon ID '{taxon_id}' not found in ontology")
        
        # Validate part_id
        part_id = identity_json.get("part_id")
        if part_id and not self.validate_part_exists(part_id):
            errors.append(f"Part ID '{part_id}' not found in ontology")
        
        # Validate transforms
        transforms = identity_json.get("transforms", [])
        if not isinstance(transforms, list):
            errors.append("transforms must be an array")
        else:
            for i, transform in enumerate(transforms):
                if not isinstance(transform, dict):
                    errors.append(f"transform[{i}] must be an object")
                    continue
                
                transform_id = transform.get("id")
                if not transform_id:
                    errors.append(f"transform[{i}] missing 'id' field")
                    continue
                
                if not self.validate_transform_exists(transform_id):
                    errors.append(f"Transform ID '{transform_id}' not found in ontology")
                    continue
                
                # Validate parameters
                params = transform.get("params", {})
                if params:
                    param_errors = self.validate_transform_params(transform_id, params)
                    for param_error in param_errors:
                        errors.append(f"transform[{i}]: {param_error}")
        
        return errors
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about loaded ontology"""
        self._ensure_loaded()
        return {
            "taxon_count": len(self._taxon_ids),
            "part_count": len(self._part_ids),
            "transform_count": len(self._transform_ids)
        }
