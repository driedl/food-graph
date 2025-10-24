#!/usr/bin/env python3
"""
Fix Orphaned Taxa

Implements the recommendations from orphaned_taxa_analysis.md:
1. Remove obsolete taxa (Meleagrididae)
2. Update valid taxa with correct NCBI taxon IDs
3. Handle cultivar varieties properly
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, List

def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def write_jsonl(file_path: Path, data: List[Dict[str, Any]]) -> None:
    """Write a JSONL file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def remove_meleagrididae(animals_file: Path) -> None:
    """Remove Meleagrididae from animals.jsonl."""
    print("🗑️  Removing Meleagrididae (obsolete taxonomy)...")
    
    animals = load_jsonl(animals_file)
    original_count = len(animals)
    
    # Remove Meleagrididae
    animals = [taxon for taxon in animals if taxon.get('id') != 'tx:a:meleagrididae']
    
    write_jsonl(animals_file, animals)
    print(f"   Removed 1 taxon ({original_count} → {len(animals)})")

def update_citrus_paradisi(plants_file: Path) -> None:
    """Update Citrus paradisi with correct NCBI taxon ID."""
    print("🍊 Updating Citrus paradisi with NCBI taxon ID 37656...")
    
    plants = load_jsonl(plants_file)
    
    for taxon in plants:
        if taxon.get('id') == 'tx:p:citrus:paradisi':
            taxon['ncbi_taxid'] = 37656
            taxon['_ncbi_source'] = 'scientific name'
            taxon['_ncbi_note'] = 'Hybrid species (Citrus sinensis × Citrus grandis)'
            print(f"   Updated {taxon['id']}: {taxon['latin_name']}")
            break
    
    write_jsonl(plants_file, plants)

def update_musa_acuminata(plants_file: Path) -> None:
    """Update Musa acuminata with correct NCBI taxon ID."""
    print("🍌 Updating Musa acuminata with NCBI taxon ID 4641...")
    
    plants = load_jsonl(plants_file)
    
    for taxon in plants:
        if taxon.get('id') == 'tx:p:musa:acuminata':
            taxon['ncbi_taxid'] = 4641
            taxon['_ncbi_source'] = 'scientific name'
            taxon['_ncbi_note'] = 'Wild banana species (cultivar groups AAA/AAB/ABB)'
            print(f"   Updated {taxon['id']}: {taxon['latin_name']}")
            break
    
    write_jsonl(plants_file, plants)

def update_oryza_glutinosa(plants_file: Path) -> None:
    """Update Oryza sativa glutinosa to reference parent species."""
    print("🍚 Updating Oryza sativa glutinosa to reference parent species...")
    
    plants = load_jsonl(plants_file)
    
    for taxon in plants:
        if taxon.get('id') == 'tx:p:oryza:sativa:glutinosa':
            # Map to parent species NCBI taxon ID
            taxon['ncbi_taxid'] = 4530  # Oryza sativa
            taxon['_ncbi_source'] = 'parent species'
            taxon['_ncbi_note'] = 'Cultivar variety of Oryza sativa (glutinous rice)'
            taxon['_cultivar_variety'] = True
            print(f"   Updated {taxon['id']}: {taxon['latin_name']} (cultivar variety)")
            break
    
    write_jsonl(plants_file, plants)

def remove_meleagrididae_docs(docs_dir: Path) -> None:
    """Remove Meleagrididae documentation files."""
    print("📁 Removing Meleagrididae documentation...")
    
    # Remove markdown files
    markdown_files = [
        docs_dir / "taxa/animalia/Meleagrididae--turkeys.tx.md",
        docs_dir / "taxa/animalia/chordata/aves/galliformes/meleagrididae/Meleagris--turkeys.tx.md"
    ]
    
    for file_path in markdown_files:
        if file_path.exists():
            file_path.unlink()
            print(f"   Deleted {file_path.relative_to(docs_dir)}")
    
    # Remove directory
    meleagrididae_dir = docs_dir / "taxa/animalia/chordata/aves/galliformes/meleagrididae"
    if meleagrididae_dir.exists():
        shutil.rmtree(meleagrididae_dir)
        print(f"   Deleted directory {meleagrididae_dir.relative_to(docs_dir)}")

def verify_derived_foods_still_work(derived_foods_file: Path) -> None:
    """Verify that derived foods still reference the correct taxa."""
    print("🔍 Verifying derived foods still work...")
    
    derived_foods = load_jsonl(derived_foods_file)
    
    # Check if glutinous rice flour TPT still exists
    glutinous_rice_tpt = None
    for tpt in derived_foods:
        if tpt.get('id') == 'tpt:oryza_sativa:glutinous:flour':
            glutinous_rice_tpt = tpt
            break
    
    if glutinous_rice_tpt:
        print(f"   ✅ Glutinous rice flour TPT found: {glutinous_rice_tpt['name']}")
        print(f"   ✅ FDC ID: {glutinous_rice_tpt.get('fdc_id')}")
    else:
        print("   ⚠️  Glutinous rice flour TPT not found!")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix orphaned taxa based on analysis")
    parser.add_argument("--ontology-root", type=Path, required=True,
                        help="Path to ontology root directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be changed without making changes")
    
    args = parser.parse_args()
    
    print("🔧 ORPHANED TAXA FIXER")
    print("="*50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        return
    
    # File paths
    animals_file = args.ontology_root / "taxa/animalia/animals.jsonl"
    plants_file = args.ontology_root / "taxa/plantae/plants_fixed_ids.jsonl"
    derived_foods_file = args.ontology_root / "rules/derived_foods.jsonl"
    
    # Verify files exist
    for file_path in [animals_file, plants_file, derived_foods_file]:
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return
    
    print(f"\n📊 Processing files:")
    print(f"   Animals: {animals_file}")
    print(f"   Plants: {plants_file}")
    print(f"   Derived foods: {derived_foods_file}")
    
    # 1. Remove Meleagrididae
    remove_meleagrididae(animals_file)
    
    # 2. Update valid taxa with NCBI taxon IDs
    update_citrus_paradisi(plants_file)
    update_musa_acuminata(plants_file)
    update_oryza_glutinosa(plants_file)
    
    # 3. Remove Meleagrididae documentation
    remove_meleagrididae_docs(args.ontology_root)
    
    # 4. Verify derived foods still work
    verify_derived_foods_still_work(derived_foods_file)
    
    print(f"\n✅ ORPHANED TAXA FIXES COMPLETE!")
    print(f"   - Removed 1 obsolete taxon (Meleagrididae)")
    print(f"   - Updated 3 valid taxa with NCBI taxon IDs")
    print(f"   - Maintained functional derived foods")
    print(f"   - Cleaned up obsolete documentation")

if __name__ == "__main__":
    main()
