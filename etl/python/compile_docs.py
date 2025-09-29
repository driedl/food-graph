#!/usr/bin/env python3
"""
compile_docs.py

Compiles taxon documentation files (.tx.md) into a structured format for the database.
Processes YAML front-matter and markdown content, validates against taxon graph,
and outputs to compiled/docs.jsonl for database ingestion.

Steps:
- Discover all .tx.md files in taxa tree
- Parse YAML front-matter and markdown body
- Validate taxon IDs exist in compiled taxa
- Render markdown to HTML
- Output structured JSONL with (taxon_id, lang) as composite key
"""

from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

def load_taxa_graph(compiled_taxa_path: Path) -> Dict[str, dict]:
    """Load compiled taxa to validate doc IDs exist."""
    taxa = {}
    if not compiled_taxa_path.exists():
        print(f"WARNING: Compiled taxa not found at {compiled_taxa_path}", file=sys.stderr)
        return taxa
    
    with compiled_taxa_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            taxon = json.loads(line)
            taxa[taxon["id"]] = taxon
    
    return taxa

def parse_doc_file(file_path: Path) -> Optional[dict]:
    """Parse a .tx.md file, extracting YAML front-matter and markdown body."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"ERROR: Failed to read {file_path}: {e}", file=sys.stderr)
        return None
    
    # Split front-matter and body
    if not content.startswith("---\n"):
        print(f"ERROR: {file_path} missing YAML front-matter", file=sys.stderr)
        return None
    
    parts = content.split("---\n", 2)
    if len(parts) != 3:
        print(f"ERROR: {file_path} malformed front-matter", file=sys.stderr)
        return None
    
    try:
        # Try to parse YAML, but handle common issues with unquoted strings containing colons
        yaml_content = parts[1]
        # Quote any unquoted strings that contain colons in display_name or summary fields
        # and escape any existing quotes in the content
        def quote_field(match):
            field_name = match.group(1)
            content = match.group(2)
            # Escape any existing quotes in the content
            escaped_content = content.replace('"', '\\"')
            return f'{field_name}: "{escaped_content}"'
        
        yaml_content = re.sub(
            r'^(display_name|summary):\s*([^"\n][^\n]*:[^\n]*)$',
            quote_field,
            yaml_content,
            flags=re.MULTILINE
        )
        front_matter = yaml.safe_load(yaml_content)
        markdown_body = parts[2].strip()
    except yaml.YAMLError as e:
        print(f"ERROR: Invalid YAML in {file_path}: {e}", file=sys.stderr)
        return None
    
    if not front_matter or "id" not in front_matter:
        print(f"ERROR: {file_path} missing required 'id' field", file=sys.stderr)
        return None
    
    return {
        "file_path": file_path,
        "front_matter": front_matter,
        "markdown_body": markdown_body
    }

# HTML rendering removed - only storing markdown

def discover_doc_files(taxa_root: Path) -> List[Path]:
    """Find all .tx.md files in the taxa tree."""
    doc_files = []
    
    # Recursively search for all .tx.md files throughout the taxa tree
    for doc_file in taxa_root.rglob("*.tx.md"):
        doc_files.append(doc_file)
    
    return sorted(doc_files)

def validate_doc(doc_data: dict, taxa_graph: Dict[str, dict]) -> List[str]:
    """Validate a documentation entry against the taxa graph."""
    errors = []
    front_matter = doc_data["front_matter"]
    
    taxon_id = front_matter.get("id")
    if not taxon_id:
        errors.append("Missing required 'id' field")
        return errors
    
    # Check taxon exists
    if taxon_id not in taxa_graph:
        errors.append(f"Taxon ID '{taxon_id}' not found in compiled taxa")
        return errors
    
    taxon = taxa_graph[taxon_id]
    
    # Validate rank matches (if provided)
    if "rank" in front_matter:
        expected_rank = taxon.get("rank")
        if expected_rank and front_matter["rank"] != expected_rank:
            errors.append(f"Rank mismatch: doc has '{front_matter['rank']}', taxon has '{expected_rank}'")
    
    # Validate required fields
    if "summary" not in front_matter:
        errors.append("Missing required 'summary' field")
    
    if not front_matter.get("summary", "").strip():
        errors.append("Summary cannot be empty")
    
    # Validate language
    lang = front_matter.get("lang", "en")
    if not isinstance(lang, str) or len(lang) != 2:
        errors.append("Language must be a 2-character code (e.g., 'en')")
    
    return errors

def process_doc_file(doc_data: dict, taxa_graph: Dict[str, dict]) -> Optional[dict]:
    """Process a single documentation file into structured output."""
    front_matter = doc_data["front_matter"]
    markdown_body = doc_data["markdown_body"]
    
    # Validate
    errors = validate_doc(doc_data, taxa_graph)
    if errors:
        file_path = doc_data["file_path"]
        print(f"ERROR: Validation failed for {file_path}:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return None
    
    # Extract fields
    taxon_id = front_matter["id"]
    lang = front_matter.get("lang", "en")
    summary = front_matter["summary"]
    
    # HTML rendering removed - only storing markdown
    
    # Generate checksum for change detection
    content_hash = hashlib.sha256(
        f"{taxon_id}:{lang}:{summary}:{markdown_body}".encode("utf-8")
    ).hexdigest()[:16]
    
    # Build output record
    updated_at = front_matter.get("updated")
    if updated_at and hasattr(updated_at, 'strftime'):
        updated_at = updated_at.strftime("%Y-%m-%d")
    elif not updated_at:
        updated_at = datetime.now().strftime("%Y-%m-%d")
    
    record = {
        "taxon_id": taxon_id,
        "lang": lang,
        "summary": summary,
        "description_md": markdown_body,
        "updated_at": updated_at,
        "checksum": content_hash,
        "rank": front_matter.get("rank"),
        "latin_name": front_matter.get("latin_name"),
        "display_name": front_matter.get("display_name"),
        "tags": front_matter.get("tags", [])
    }
    
    return record

def main():
    ap = argparse.ArgumentParser(description="Compile taxon documentation files")
    ap.add_argument("--taxa-root", default="data/ontology/taxa", help="Path to data/ontology/taxa/")
    ap.add_argument("--compiled-taxa", default="data/ontology/compiled/taxa.jsonl", help="Path to compiled taxa JSONL")
    ap.add_argument("--out", default="data/ontology/compiled/docs.jsonl", help="Output JSONL file")
    args = ap.parse_args()
    
    taxa_root = Path(args.taxa_root)
    compiled_taxa_path = Path(args.compiled_taxa)
    out_path = Path(args.out)
    
    # Ensure output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load taxa graph for validation
    print("Loading taxa graph...")
    taxa_graph = load_taxa_graph(compiled_taxa_path)
    print(f"Loaded {len(taxa_graph)} taxa")
    
    # Discover documentation files
    print("Discovering documentation files...")
    doc_files = discover_doc_files(taxa_root)
    print(f"Found {len(doc_files)} documentation files")
    
    if not doc_files:
        print("No documentation files found. Creating empty output.")
        with out_path.open("w", encoding="utf-8") as f:
            pass
        return
    
    # Process each documentation file
    records = []
    errors = 0
    
    for doc_file in doc_files:
        print(f"Processing {doc_file.relative_to(taxa_root)}...")
        
        doc_data = parse_doc_file(doc_file)
        if not doc_data:
            errors += 1
            continue
        
        record = process_doc_file(doc_data, taxa_graph)
        if not record:
            errors += 1
            continue
        
        records.append(record)
    
    # Check for duplicate (taxon_id, lang) combinations
    seen = set()
    for record in records:
        key = (record["taxon_id"], record["lang"])
        if key in seen:
            print(f"ERROR: Duplicate (taxon_id, lang) combination: {key}", file=sys.stderr)
            errors += 1
        seen.add(key)
    
    if errors > 0:
        print(f"Compilation failed with {errors} errors", file=sys.stderr)
        sys.exit(1)
    
    # Sort records by taxon_id, then lang
    records.sort(key=lambda r: (r["taxon_id"], r["lang"]))
    
    # Write output
    with out_path.open("w", encoding="utf-8") as f:
        for record in records:
            try:
                f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            except TypeError as e:
                print(f"ERROR: JSON serialization failed for record {record.get('taxon_id', 'unknown')}: {e}")
                print(f"Record keys: {list(record.keys())}")
                for k, v in record.items():
                    print(f"  {k}: {type(v)} = {repr(v)}")
                raise
    
    print(f"✓ Compiled {len(records)} documentation records → {out_path}")

if __name__ == "__main__":
    main()
