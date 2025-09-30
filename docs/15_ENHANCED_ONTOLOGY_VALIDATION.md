# Enhanced Ontology Validation System

## Overview

This document outlines a comprehensive plan to enhance the food graph ontology validation system to prevent data integrity issues, improve build reliability, and ensure consistent data quality across all ontology components.

## Current State Analysis

### Existing Validation System

The current validation pipeline consists of:

1. **Taxa Validation** (`etl/python/validate_taxa.py`)
   - Validates taxonomic hierarchy and file alignment
   - Checks rank terminology per kingdom
   - Ensures parent-child relationships are consistent
   - Prevents product nouns masquerading as taxa

2. **Database Verification** (`etl/src/pipeline/steps/verify.ts`)
   - Basic database connectivity tests
   - FTS search functionality verification
   - Smoke tests for composition model

3. **Pipeline Steps** (from `etl/src/pipeline/config.ts`):
   ```
   validate → compile-taxa → compile-docs → build-db → verify → doc-report
   ```

### Identified Gaps

Recent issues revealed several validation gaps:

- **Duplicate Detection**: No validation for duplicate IDs in metadata files (parts.json, transforms.json, attributes.json)
- **Cross-Reference Validation**: No verification that referenced IDs actually exist
- **JSON Schema Validation**: Schema files exist but aren't actively used for validation
- **Rule Consistency**: No validation of rule file logic and cross-references
- **Data Quality**: No systematic checks for data quality issues

## Proposed Enhancement Plan

### Phase 1: Core Data Validation (HIGH Priority)

#### 1.1 Duplicate Detection

**Target Files:**

- `data/ontology/parts.json`
- `data/ontology/transforms.json`
- `data/ontology/attributes.json`
- `data/ontology/animal_cuts/*.json`

**Validation Logic:**

```python
def check_duplicate_ids(data_list, file_name):
    """Check for duplicate IDs in JSON data"""
    seen_ids = set()
    duplicates = []

    for i, item in enumerate(data_list):
        item_id = item.get('id')
        if not item_id:
            continue
        if item_id in seen_ids:
            duplicates.append((i, item_id))
        seen_ids.add(item_id)

    if duplicates:
        for line_num, dup_id in duplicates:
            fail(f"{file_name}:{line_num}: duplicate ID '{dup_id}'")
```

#### 1.2 JSON Schema Validation

**Existing Schema Files:**

- `data/sql/schema/part.schema.json`
- `data/sql/schema/transform.schema.json`
- `data/sql/schema/attribute.schema.json`
- `data/sql/schema/taxon.schema.json`

**Implementation:**

```python
import jsonschema

def validate_against_schema(data, schema_path, file_name):
    """Validate JSON data against JSON schema"""
    with open(schema_path, 'r') as f:
        schema = json.load(f)

    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        fail(f"{file_name}: schema validation failed: {e.message}")
```

#### 1.3 Cross-Reference Validation

**Validation Targets:**

- Part aliases referencing non-existent parts
- Rule files referencing non-existent taxa/parts/transforms
- Animal cuts referencing non-existent taxa

**Implementation Pattern:**

```python
def validate_cross_references():
    """Validate that all referenced IDs exist"""
    # Load all valid IDs
    valid_parts = {p['id'] for p in parts_data}
    valid_taxa = {t['id'] for t in taxa_data}
    valid_transforms = {t['id'] for t in transforms_data}

    # Check part aliases
    for alias in part_aliases:
        if alias['part_id'] not in valid_parts:
            fail(f"part_aliases.jsonl: unknown part_id '{alias['part_id']}'")
```

### Phase 2: Rule Consistency Validation (MEDIUM Priority)

#### 2.1 Rule File Validation

**Target Files:**

- `data/ontology/rules/parts_applicability.jsonl`
- `data/ontology/rules/transform_applicability.jsonl`
- `data/ontology/rules/implied_parts.jsonl`
- `data/ontology/rules/name_overrides.jsonl`
- `data/ontology/rules/taxon_part_synonyms.jsonl`
- `data/ontology/rules/part_aliases.jsonl`
- `data/ontology/rules/taxon_part_policy.json`

**Validation Requirements:**

```python
RULE_SCHEMAS = {
    'parts_applicability.jsonl': {
        'required': ['part', 'applies_to'],
        'optional': ['exclude'],
        'types': {
            'part': str,
            'applies_to': list,
            'exclude': list
        }
    },
    'transform_applicability.jsonl': {
        'required': ['transform', 'applies_to'],
        'optional': ['exclude'],
        'types': {
            'transform': str,
            'applies_to': list,
            'exclude': list
        }
    },
    # ... additional schemas
}
```

#### 2.2 Logical Consistency Checks

**Validation Logic:**

```python
def validate_rule_consistency():
    """Validate logical consistency of rules"""

    # Check applies_to prefixes exist
    for rule in parts_applicability:
        for prefix in rule.get('applies_to', []):
            if not any(taxon_id.startswith(prefix) for taxon_id in all_taxa):
                fail(f"No taxa found matching prefix '{prefix}'")

    # Check transform applicability combinations
    for rule in transform_applicability:
        for applies_to in rule.get('applies_to', []):
            taxon_prefix = applies_to.get('taxon_prefix')
            parts = applies_to.get('parts', [])

            # Verify taxon prefix exists
            if not any(t.startswith(taxon_prefix) for t in all_taxa):
                fail(f"Unknown taxon_prefix '{taxon_prefix}'")

            # Verify parts exist
            for part_id in parts:
                if part_id not in valid_parts:
                    fail(f"Unknown part_id '{part_id}' in transform rule")
```

### Phase 3: Data Quality Validation (LOW Priority)

#### 3.1 Naming Consistency

**Checks:**

- Part IDs follow naming conventions (part:category:name)
- Transform IDs follow conventions (tf:action)
- Synonym quality (no empty strings, duplicates)

#### 3.2 Coverage Analysis

**Analysis:**

- Taxa with no applicable parts
- Parts with no applicable transforms
- Missing documentation coverage

## Implementation Strategy

### New Validation Steps

Add these steps to `etl/src/pipeline/config.ts`:

```typescript
{
  id: 'validate-metadata',
  name: 'Validate metadata files',
  description: 'Check for duplicates and validate against schemas',
  command: 'python3',
  args: ['etl/python/validate_metadata.py', '--ontology-root', 'data/ontology'],
  dependencies: []
},
{
  id: 'validate-rules',
  name: 'Validate rule files',
  description: 'Validate rule consistency and cross-references',
  command: 'python3',
  args: ['etl/python/validate_rules.py', '--ontology-root', 'data/ontology'],
  dependencies: ['validate-metadata']
},
{
  id: 'validate-consistency',
  name: 'Validate data consistency',
  description: 'Cross-reference validation and logical consistency',
  command: 'python3',
  args: ['etl/python/validate_consistency.py', '--ontology-root', 'data/ontology'],
  dependencies: ['validate-rules', 'compile-taxa']
}
```

### New Validation Scripts

#### `etl/python/validate_metadata.py`

```python
#!/usr/bin/env python3
"""
Validate core ontology metadata files for duplicates and schema compliance.
"""

import argparse
import json
import jsonschema
from pathlib import Path
from typing import Dict, List, Any

def check_duplicates(data: List[Dict], file_name: str) -> int:
    """Check for duplicate IDs in data list"""
    errors = 0
    seen_ids = set()

    for i, item in enumerate(data):
        item_id = item.get('id')
        if not item_id:
            continue
        if item_id in seen_ids:
            print(f"ERROR: {file_name}:{i+1}: duplicate ID '{item_id}'")
            errors += 1
        seen_ids.add(item_id)

    return errors

def validate_schema(data: List[Dict], schema_path: Path, file_name: str) -> int:
    """Validate data against JSON schema"""
    if not schema_path.exists():
        print(f"WARNING: Schema file not found: {schema_path}")
        return 0

    errors = 0
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        print(f"ERROR: {file_name}: schema validation failed: {e.message}")
        errors += 1
    except Exception as e:
        print(f"ERROR: {file_name}: schema validation error: {e}")
        errors += 1

    return errors

def validate_metadata_files(ontology_root: Path) -> int:
    """Validate all metadata files"""
    total_errors = 0

    # Define files to validate
    files_to_check = [
        ('parts.json', 'data/sql/schema/part.schema.json'),
        ('transforms.json', 'data/sql/schema/transform.schema.json'),
        ('attributes.json', 'data/sql/schema/attribute.schema.json')
    ]

    for file_name, schema_name in files_to_check:
        file_path = ontology_root / file_name
        schema_path = Path(schema_name)

        if not file_path.exists():
            print(f"WARNING: File not found: {file_path}")
            continue

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            print(f"Validating {file_name}...")

            # Check duplicates
            total_errors += check_duplicates(data, file_name)

            # Validate schema
            total_errors += validate_schema(data, schema_path, file_name)

        except json.JSONDecodeError as e:
            print(f"ERROR: {file_name}: invalid JSON: {e}")
            total_errors += 1
        except Exception as e:
            print(f"ERROR: {file_name}: {e}")
            total_errors += 1

    return total_errors

def main():
    parser = argparse.ArgumentParser(description='Validate ontology metadata files')
    parser.add_argument('--ontology-root', default='data/ontology',
                       help='Path to ontology root directory')
    args = parser.parse_args()

    ontology_root = Path(args.ontology_root)
    errors = validate_metadata_files(ontology_root)

    if errors == 0:
        print("✓ Metadata validation passed.")
        return 0
    else:
        print(f"✗ Metadata validation failed with {errors} errors.")
        return 1

if __name__ == "__main__":
    exit(main())
```

#### `etl/python/validate_rules.py`

```python
#!/usr/bin/env python3
"""
Validate rule files for format, consistency, and cross-references.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Set

def read_jsonl(path: Path) -> List[Dict]:
    """Read JSONL file, skipping comment lines"""
    items = []
    with open(path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"ERROR: {path}:{line_num}: invalid JSON: {e}")
                return []
    return items

def validate_rule_format(rule: Dict, rule_type: str, line_num: int) -> int:
    """Validate rule format against schema"""
    errors = 0

    # Define rule schemas
    schemas = {
        'parts_applicability': {
            'required': ['part', 'applies_to'],
            'optional': ['exclude']
        },
        'transform_applicability': {
            'required': ['transform', 'applies_to'],
            'optional': ['exclude']
        },
        'implied_parts': {
            'required': ['applies_to', 'part'],
            'optional': ['exclude']
        },
        'name_overrides': {
            'required': ['taxon_id', 'part_id', 'name'],
            'optional': ['display_name']
        },
        'taxon_part_synonyms': {
            'required': ['taxon_id', 'part_id', 'synonyms'],
            'optional': []
        },
        'part_aliases': {
            'required': ['part_id', 'aliases'],
            'optional': []
        }
    }

    schema = schemas.get(rule_type)
    if not schema:
        return errors

    # Check required fields
    for field in schema['required']:
        if field not in rule:
            print(f"ERROR: {rule_type}:{line_num}: missing required field '{field}'")
            errors += 1

    # Check field types
    if 'applies_to' in rule and not isinstance(rule['applies_to'], list):
        print(f"ERROR: {rule_type}:{line_num}: 'applies_to' must be a list")
        errors += 1

    if 'exclude' in rule and not isinstance(rule['exclude'], list):
        print(f"ERROR: {rule_type}:{line_num}: 'exclude' must be a list")
        errors += 1

    if 'synonyms' in rule and not isinstance(rule['synonyms'], list):
        print(f"ERROR: {rule_type}:{line_num}: 'synonyms' must be a list")
        errors += 1

    if 'aliases' in rule and not isinstance(rule['aliases'], list):
        print(f"ERROR: {rule_type}:{line_num}: 'aliases' must be a list")
        errors += 1

    return errors

def validate_rule_files(ontology_root: Path) -> int:
    """Validate all rule files"""
    total_errors = 0
    rules_dir = ontology_root / 'rules'

    if not rules_dir.exists():
        print(f"WARNING: Rules directory not found: {rules_dir}")
        return 0

    # Define rule files to validate
    rule_files = [
        'parts_applicability.jsonl',
        'transform_applicability.jsonl',
        'implied_parts.jsonl',
        'name_overrides.jsonl',
        'taxon_part_synonyms.jsonl',
        'part_aliases.jsonl'
    ]

    for file_name in rule_files:
        file_path = rules_dir / file_name
        if not file_path.exists():
            print(f"WARNING: Rule file not found: {file_path}")
            continue

        print(f"Validating {file_name}...")
        rules = read_jsonl(file_path)

        if not rules:  # read_jsonl already printed errors
            total_errors += 1
            continue

        rule_type = file_name.replace('.jsonl', '')

        for line_num, rule in enumerate(rules, 1):
            total_errors += validate_rule_format(rule, rule_type, line_num)

    return total_errors

def main():
    parser = argparse.ArgumentParser(description='Validate ontology rule files')
    parser.add_argument('--ontology-root', default='data/ontology',
                       help='Path to ontology root directory')
    args = parser.parse_args()

    ontology_root = Path(args.ontology_root)
    errors = validate_rule_files(ontology_root)

    if errors == 0:
        print("✓ Rule validation passed.")
        return 0
    else:
        print(f"✗ Rule validation failed with {errors} errors.")
        return 1

if __name__ == "__main__":
    exit(main())
```

#### `etl/python/validate_consistency.py`

```python
#!/usr/bin/env python3
"""
Validate cross-references and logical consistency across ontology data.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Set

def load_taxa_data(compiled_dir: Path) -> Set[str]:
    """Load all taxon IDs from compiled taxa data"""
    taxa_file = compiled_dir / 'taxa' / 'taxa.jsonl'
    if not taxa_file.exists():
        return set()

    taxa_ids = set()
    with open(taxa_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            try:
                obj = json.loads(line)
                taxa_ids.add(obj['id'])
            except (json.JSONDecodeError, KeyError):
                continue

    return taxa_ids

def load_metadata_ids(ontology_root: Path) -> Dict[str, Set[str]]:
    """Load all IDs from metadata files"""
    ids = {
        'parts': set(),
        'transforms': set(),
        'attributes': set()
    }

    files = {
        'parts': ontology_root / 'parts.json',
        'transforms': ontology_root / 'transforms.json',
        'attributes': ontology_root / 'attributes.json'
    }

    for category, file_path in files.items():
        if not file_path.exists():
            continue

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            for item in data:
                if 'id' in item:
                    ids[category].add(item['id'])
        except (json.JSONDecodeError, KeyError):
            continue

    return ids

def validate_cross_references(ontology_root: Path, compiled_dir: Path) -> int:
    """Validate cross-references between data files"""
    errors = 0

    # Load reference data
    taxa_ids = load_taxa_data(compiled_dir)
    metadata_ids = load_metadata_ids(ontology_root)

    # Validate part aliases
    part_aliases_file = ontology_root / 'rules' / 'part_aliases.jsonl'
    if part_aliases_file.exists():
        print("Validating part aliases cross-references...")
        with open(part_aliases_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('//'):
                    continue
                try:
                    rule = json.loads(line)
                    part_id = rule.get('part_id')
                    if part_id and part_id not in metadata_ids['parts']:
                        print(f"ERROR: part_aliases.jsonl:{line_num}: unknown part_id '{part_id}'")
                        errors += 1
                except json.JSONDecodeError:
                    continue

    # Validate parts applicability
    parts_app_file = ontology_root / 'rules' / 'parts_applicability.jsonl'
    if parts_app_file.exists():
        print("Validating parts applicability cross-references...")
        with open(parts_app_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('//'):
                    continue
                try:
                    rule = json.loads(line)
                    part_id = rule.get('part')
                    if part_id and part_id not in metadata_ids['parts']:
                        print(f"ERROR: parts_applicability.jsonl:{line_num}: unknown part '{part_id}'")
                        errors += 1

                    # Check applies_to prefixes
                    for prefix in rule.get('applies_to', []):
                        if not any(taxon_id.startswith(prefix) for taxon_id in taxa_ids):
                            print(f"ERROR: parts_applicability.jsonl:{line_num}: no taxa match prefix '{prefix}'")
                            errors += 1
                except json.JSONDecodeError:
                    continue

    return errors

def main():
    parser = argparse.ArgumentParser(description='Validate ontology consistency')
    parser.add_argument('--ontology-root', default='data/ontology',
                       help='Path to ontology root directory')
    parser.add_argument('--compiled-dir', default='etl/dist/compiled',
                       help='Path to compiled data directory')
    args = parser.parse_args()

    ontology_root = Path(args.ontology_root)
    compiled_dir = Path(args.compiled_dir)

    errors = validate_cross_references(ontology_root, compiled_dir)

    if errors == 0:
        print("✓ Consistency validation passed.")
        return 0
    else:
        print(f"✗ Consistency validation failed with {errors} errors.")
        return 1

if __name__ == "__main__":
    exit(main())
```

## Integration Instructions

### 1. Update Pipeline Configuration

Add the new validation steps to `etl/src/pipeline/config.ts` in the appropriate order:

```typescript
// Add after existing steps
{
  id: 'validate-metadata',
  name: 'Validate metadata files',
  description: 'Check for duplicates and validate against schemas',
  command: 'python3',
  args: ['etl/python/validate_metadata.py', '--ontology-root', 'data/ontology'],
  dependencies: []
},
{
  id: 'validate-rules',
  name: 'Validate rule files',
  description: 'Validate rule consistency and cross-references',
  command: 'python3',
  args: ['etl/python/validate_rules.py', '--ontology-root', 'data/ontology'],
  dependencies: ['validate-metadata']
},
{
  id: 'validate-consistency',
  name: 'Validate data consistency',
  description: 'Cross-reference validation and logical consistency',
  command: 'python3',
  args: ['etl/python/validate_consistency.py', '--ontology-root', 'data/ontology'],
  dependencies: ['validate-rules', 'compile-taxa']
}
```

### 2. Update Existing Validation Step

Modify the existing `validate` step to depend on the new metadata validation:

```typescript
{
  id: 'validate',
  name: 'Validate ontology data',
  description: 'Validate taxonomic data integrity and consistency',
  command: 'python3',
  args: ['etl/python/validate_taxa.py', '--taxa-root', 'data/ontology/taxa'],
  dependencies: ['validate-metadata'] // Add this dependency
}
```

### 3. Install Dependencies

Add `jsonschema` to the Python requirements:

```bash
# Add to requirements.txt or install directly
pip install jsonschema
```

### 4. Test Implementation

Run the validation pipeline to test:

```bash
# Test individual validation steps
python3 etl/python/validate_metadata.py --ontology-root data/ontology
python3 etl/python/validate_rules.py --ontology-root data/ontology
python3 etl/python/validate_consistency.py --ontology-root data/ontology --compiled-dir etl/dist/compiled

# Test full pipeline
pnpm etl:build
```

## Error Handling

### Error Format

All validation scripts should follow this error format:

```
ERROR: filename:line_number: description of error
```

### Exit Codes

- `0`: Validation passed
- `1`: Validation failed with errors

### Error Categories

1. **Duplicate IDs**: Prevented by metadata validation
2. **Schema violations**: Caught by schema validation
3. **Cross-reference errors**: Caught by consistency validation
4. **Rule format errors**: Caught by rule validation

## Future Enhancements

### Performance Optimization

- Parallel validation of independent files
- Incremental validation (only check changed files)
- Caching of validation results

### Advanced Validation

- Semantic validation (e.g., part kinds match taxon kingdoms)
- Statistical analysis (e.g., coverage metrics)
- Automated fix suggestions

### Integration Features

- Pre-commit hooks for validation
- IDE integration for real-time validation
- CI/CD pipeline integration

## Success Metrics

- **Build Reliability**: Zero unexpected build failures from data issues
- **Error Detection**: Catch 95%+ of data integrity issues before build
- **Performance**: Complete validation in <30 seconds
- **Developer Experience**: Clear, actionable error messages

## Implementation Priority

1. **Phase 1.1** (Immediate): Duplicate detection and basic schema validation
2. **Phase 1.2** (Week 1): Cross-reference validation
3. **Phase 1.3** (Week 2): Rule file validation
4. **Phase 2** (Month 1): Advanced consistency checks
5. **Phase 3** (Month 2+): Data quality and performance validation

This implementation will significantly improve the reliability and maintainability of the food graph ontology system.
