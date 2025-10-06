from __future__ import annotations
import json, re, sys
from pathlib import Path
from typing import Dict, List, Optional

import yaml  # ensure present in your venv

def _load_taxa_graph(compiled_taxa_path: Path) -> Dict[str, dict]:
    taxa = {}
    if not compiled_taxa_path.exists():
        print(f"WARNING: Compiled taxa not found at {compiled_taxa_path}", file=sys.stderr)
        return taxa
    with compiled_taxa_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"): continue
            o = json.loads(line)
            taxa[o["id"]] = o
    return taxa

def _parse_doc_file(file_path: Path) -> Optional[dict]:
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        print(f"ERROR: {file_path} missing YAML front-matter", file=sys.stderr); return None
    parts = content.split("---\n", 2)
    if len(parts) != 3:
        print(f"ERROR: {file_path} malformed front-matter", file=sys.stderr); return None
    yaml_content = re.sub(
        r'^(display_name|summary):\s*([^"\n][^\n]*:[^\n]*)$',
        lambda m: f'{m.group(1)}: "{m.group(2).replace(chr(34), chr(92) + chr(34))}"',
        parts[1],
        flags=re.MULTILINE
    )
    try:
        front_matter = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError as e:
        print(f"ERROR: Invalid YAML in {file_path}: {e}", file=sys.stderr); return None
    body = parts[2].strip()
    if "id" not in front_matter:
        print(f"ERROR: {file_path} missing required 'id' field", file=sys.stderr); return None
    return {"file_path": file_path, "front_matter": front_matter, "markdown_body": body}

def compile_docs_into(*, taxa_root: Path, compiled_taxa_path: Path, out_docs_path: Path, verbose: bool = False) -> int:
    out_docs_path.parent.mkdir(parents=True, exist_ok=True)

    # Load graph for validation
    taxa_graph = _load_taxa_graph(compiled_taxa_path)
    if verbose: print(f"Loaded {len(taxa_graph)} taxa for doc validation")

    # Discover *.tx.md
    doc_files = sorted(taxa_root.rglob("*.tx.md"))
    if verbose: print(f"Found {len(doc_files)} .tx.md files")

    records, seen = [], set()
    errors = 0

    for doc_file in doc_files:
        data = _parse_doc_file(doc_file)
        if not data: errors += 1; continue

        fm = data["front_matter"]
        tid = fm.get("id")
        if tid not in taxa_graph:
            print(f"ERROR: {doc_file}: Taxon '{tid}' not found in compiled taxa", file=sys.stderr)
            errors += 1; continue

        lang = fm.get("lang", "en")
        summary = (fm.get("summary") or "").strip()
        if not summary:
            print(f"ERROR: {doc_file}: summary is required", file=sys.stderr); errors += 1; continue

        key = (tid, lang)
        if key in seen:
            print(f"ERROR: Duplicate doc for {key}", file=sys.stderr); errors += 1; continue
        seen.add(key)

        # no HTML render—store markdown
        from hashlib import sha256
        content_hash = sha256(f"{tid}:{lang}:{summary}:{data['markdown_body']}".encode("utf-8")).hexdigest()[:16]
        from datetime import datetime
        updated = fm.get("updated")
        if hasattr(updated, "strftime"): updated = updated.strftime("%Y-%m-%d")
        if not updated: updated = datetime.now().strftime("%Y-%m-%d")

        records.append({
            "taxon_id": tid,
            "lang": lang,
            "summary": summary,
            "description_md": data["markdown_body"],
            "updated_at": updated,
            "checksum": content_hash,
            "rank": fm.get("rank"),
            "latin_name": fm.get("latin_name"),
            "display_name": fm.get("display_name"),
            "tags": fm.get("tags", []),
        })

    if errors:
        print(f"Compilation failed with {errors} doc errors", file=sys.stderr)
        return 1

    records.sort(key=lambda r: (r["taxon_id"], r["lang"]))
    with out_docs_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    if verbose: print(f"✓ Compiled {len(records)} docs → {out_docs_path}")
    return 0
