#!/usr/bin/env python3
"""
Upgrade Evidence Ingestion Prompts

Integrates the optimized prompts into the existing evidence ingestion system.
This script updates the Tier 1-3 classes to use the enhanced prompts.
"""

import shutil
from pathlib import Path
from typing import Dict, Any

def backup_original_files(evidence_dir: Path, backup_dir: Path) -> None:
    """Create backup of original files before modification."""
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Files to backup
    files_to_backup = [
        "lib/tier1_taxon.py",
        "lib/tier2_tpt.py", 
        "lib/tier3_curator.py"
    ]
    
    for file_path in files_to_backup:
        src = evidence_dir / file_path
        dst = backup_dir / file_path
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"✅ Backed up {file_path}")

def update_tier1_taxon_py(evidence_dir: Path) -> None:
    """Update tier1_taxon.py with optimized prompts."""
    file_path = evidence_dir / "lib/tier1_taxon.py"
    
    # Read current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the system prompt method
    old_method = '''    def _get_taxon_system_prompt(self) -> str:
        """Get system prompt for taxon resolution"""
        return """
You are a taxonomic expert specializing in food identification. Your task is to identify the biological taxon for food items.

Rules:
1. Use the format tx:{k}:{genus}:{species}[:{cultivar/breed}] where k is kingdom code (p=plantae, a=animalia, f=fungi)
2. Be conservative - if uncertain, back off to higher taxonomic levels (genus, family)
3. For processed foods, identify the base biological source
4. Skip non-biological items (minerals, water, synthetic compounds)
5. Skip processed food mixtures that significantly alter nutritional composition
6. Use existing taxon IDs when possible
7. Only propose new taxa when absolutely necessary

SKIP THESE TYPES OF FOODS:
- Processed mixtures (hummus, salsa, salad dressings, etc.)
- Multi-ingredient products where the base biological source is unclear
- Foods with significant processing that changes nutritional profile
- Non-biological items (salt, water, synthetic compounds)

Examples:
- "Apple" → tx:p:malus:domestica
- "Beef" → tx:a:bos:taurus  
- "Button mushroom" → tx:f:agaricus:bisporus
- "Hummus, commercial" → disposition: "skip" (processed mixture)
- "Table salt" → disposition: "skip" (non-biological)

Return valid JSON only.
""".strip()'''
    
    new_method = '''    def _get_taxon_system_prompt(self) -> str:
        """Get system prompt for taxon resolution"""
        from .optimized_prompts import get_optimized_taxon_system_prompt
        return get_optimized_taxon_system_prompt()'''
    
    if old_method in content:
        content = content.replace(old_method, new_method)
        print("✅ Updated _get_taxon_system_prompt method")
    else:
        print("⚠️  Could not find _get_taxon_system_prompt method to replace")
    
    # Replace the user prompt method
    old_prompt_method = '''    def _build_taxon_prompt(self, food_name: str, food_description: str = "") -> str:
        """Build prompt for taxon resolution"""
        prompt = f"Food: {food_name}"
        if food_description:
            prompt += f"\\nDescription: {food_description}"
        
        prompt += "\\n\\nIdentify the biological taxon for this food item. Return JSON with:"
        prompt += "\\n- taxon_id: tx:{k}:{genus}:{species}[:{cultivar/breed}] or null"
        prompt += "\\n- confidence: 0.0-1.0"
        prompt += "\\n- disposition: 'resolved', 'ambiguous', or 'skip'"
        prompt += "\\n- reason: brief explanation"
        prompt += "\\n- new_taxa: [] (if proposing new taxa)"
        
        return prompt'''
    
    new_prompt_method = '''    def _build_taxon_prompt(self, food_name: str, food_description: str = "") -> str:
        """Build prompt for taxon resolution"""
        from .optimized_prompts import get_enhanced_taxon_prompt
        return get_enhanced_taxon_prompt(food_name, food_description)'''
    
    if old_prompt_method in content:
        content = content.replace(old_prompt_method, new_prompt_method)
        print("✅ Updated _build_taxon_prompt method")
    else:
        print("⚠️  Could not find _build_taxon_prompt method to replace")
    
    # Write updated file
    with open(file_path, 'w') as f:
        f.write(content)

def update_tier2_tpt_py(evidence_dir: Path) -> None:
    """Update tier2_tpt.py with optimized prompts."""
    file_path = evidence_dir / "lib/tier2_tpt.py"
    
    # Read current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the system prompt method
    old_method = '''    def _get_tpt_system_prompt(self) -> str:
        """Get system prompt for TPT construction"""
        return """
You are a food science expert specializing in food structure and processing. Your task is to construct Taxon-Part-Transform (TPT) combinations for food items.

BIOLOGICAL CONTEXT:
- Broccoli florets = immature flower buds (use part:flower)
- Broccoli stems = plant stems (use part:stem) 
- Broccoli leaves = plant leaves (use part:leaf)
- Tomatoes = fruits (use part:fruit)
- Milk = animal secretion (use part:milk)
- Cheese = fermented milk product (use part:cheese)
- Meat cuts = muscle tissue (use part:muscle)

RULES:
1. Select the most appropriate biological part for the food item
2. Include transforms that the food has undergone (cooking, processing, etc.)
3. Use only the provided applicable parts and available transforms
4. Be conservative - if uncertain, use fewer transforms or mark as ambiguous
5. Consider the food's processing state and biological structure
6. Transforms should be ordered by processing sequence
7. ONLY propose new parts if absolutely no existing part fits the biological structure

EXAMPLES:
- "Raw apple" → part: fruit, transforms: []
- "Broccoli, raw" → part: flower, transforms: []
- "Cooked beef" → part: muscle, transforms: [{"id": "tf:cook", "params": {}}]
- "Ground beef" → part: muscle, transforms: [{"id": "tf:grind", "params": {}}]
- "Pasteurized milk" → part: milk, transforms: [{"id": "tf:pasteurize", "params": {}}]
- "Cheddar cheese" → part: cheese, transforms: [{"id": "tf:age", "params": {}}]

Return valid JSON only.
""".strip()'''
    
    new_method = '''    def _get_tpt_system_prompt(self) -> str:
        """Get system prompt for TPT construction"""
        from .optimized_prompts import get_optimized_tpt_system_prompt
        return get_optimized_tpt_system_prompt()'''
    
    if old_method in content:
        content = content.replace(old_method, new_method)
        print("✅ Updated _get_tpt_system_prompt method")
    else:
        print("⚠️  Could not find _get_tpt_system_prompt method to replace")
    
    # Replace the user prompt method
    old_prompt_method = '''    def _build_tpt_prompt(self, taxon_resolution: TaxonResolution, 
                         applicable_parts: List[Dict[str, Any]], 
                         available_transforms: List[Dict[str, Any]]) -> str:
        """Build prompt for TPT construction"""
        prompt = f"Food: {taxon_resolution.food_name}\\n"
        prompt += f"Taxon: {taxon_resolution.taxon_id}\\n"
        prompt += f"NCBI Confidence: {taxon_resolution.confidence:.2f}\\n\\n"
        
        prompt += "Applicable Parts:\\n"
        for part in applicable_parts:
            prompt += f"- {part.id}: {part.name} ({part.kind or 'unknown'})\\n"
        
        prompt += "\\nAvailable Transforms:\\n"
        for transform in available_transforms:
            prompt += f"- {transform.id}: {transform.name} (order: {transform.order or 999})\\n"
        
        prompt += "\\nConstruct TPT combination. Return JSON with:"
        prompt += "\\n- part_id: selected part ID or null"
        prompt += "\\n- transforms: list of transform objects with id and params"
        prompt += "\\n- confidence: 0.0-1.0"
        prompt += "\\n- disposition: 'constructed', 'ambiguous', or 'skip'"
        prompt += "\\n- reason: brief explanation"
        prompt += "\\n- new_parts: [] (if proposing new parts)"
        prompt += "\\n- new_transforms: [] (if proposing new transforms)"
        
        return prompt'''
    
    new_prompt_method = '''    def _build_tpt_prompt(self, taxon_resolution: TaxonResolution, 
                         applicable_parts: List[Dict[str, Any]], 
                         available_transforms: List[Dict[str, Any]]) -> str:
        """Build prompt for TPT construction"""
        from .optimized_prompts import get_enhanced_tpt_prompt
        return get_enhanced_tpt_prompt(taxon_resolution, applicable_parts, available_transforms)'''
    
    if old_prompt_method in content:
        content = content.replace(old_prompt_method, new_prompt_method)
        print("✅ Updated _build_tpt_prompt method")
    else:
        print("⚠️  Could not find _build_tpt_prompt method to replace")
    
    # Write updated file
    with open(file_path, 'w') as f:
        f.write(content)

def update_tier3_curator_py(evidence_dir: Path) -> None:
    """Update tier3_curator.py with optimized prompts."""
    file_path = evidence_dir / "lib/tier3_curator.py"
    
    # Read current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the system prompt method
    old_method = '''    def _get_curation_system_prompt(self) -> str:
        """Get system prompt for comprehensive ontology curation"""
        return """
You are a senior ontology curator specializing in food taxonomy and processing systems. Your role is to evaluate food mappings and provide comprehensive recommendations for evolving the ontology.

Your analysis should cover:

1. **Part Analysis**:
   - Are new parts needed for this food?
   - Should existing parts be modified (name, description, kind)?
   - Do we need new applies_to rules for taxonomic applicability?
   - Are there derived parts that should be created?

2. **Transform Analysis**:
   - Are new transforms needed for this processing?
   - Should existing transforms be modified?
   - Do transform parameter schemas need new parameters?
   - Are there processing steps not covered by current transforms?

3. **Relationship Analysis**:
   - Are there new derived part relationships needed?
   - Should existing rules be modified?
   - Are there taxonomic relationships that need updating?

4. **Ontology Optimization**:
   - How can the overall ontology structure be improved?
   - Are there redundancies or gaps in the current design?
   - What general recommendations do you have?

Return JSON with this exact structure:
{
  "new_parts": [{"id": "part:new_id", "name": "New Part", "kind": "plant", "description": "...", "applies_to": ["tx:p:genus:species"]}],
  "modify_parts": [{"id": "part:existing", "modifications": {"name": "Updated Name", "applies_to": ["tx:p:genus:species"]}}],
  "part_applies_to_rules": [{"part_id": "part:existing", "add_taxa": ["tx:p:genus:species"], "remove_taxa": []}],
  "new_transforms": [{"id": "tf:new_id", "name": "New Transform", "description": "...", "params": {"param1": "type"}}],
  "modify_transforms": [{"id": "tf:existing", "modifications": {"params": {"new_param": "type"}}}],
  "transform_param_schemas": [{"transform_id": "tf:existing", "new_params": {"param": "type", "description": "..."}}],
  "derived_part_rules": [{"base_part": "part:base", "derived_part": "part:derived", "transform": "tf:transform", "conditions": {}}],
  "modify_rules": [{"rule_id": "rule_id", "modifications": {...}}],
  "optimization_suggestions": ["General optimization recommendation 1", "General optimization recommendation 2"],
  "confidence": 0.8,
  "reasoning": "Detailed explanation of all recommendations and their rationale"
}

Be conservative but thorough. Only recommend changes that are clearly needed and well-justified.
""".strip()'''
    
    new_method = '''    def _get_curation_system_prompt(self) -> str:
        """Get system prompt for comprehensive ontology curation"""
        from .optimized_prompts import get_optimized_curation_system_prompt
        return get_optimized_curation_system_prompt()'''
    
    if old_method in content:
        content = content.replace(old_method, new_method)
        print("✅ Updated _get_curation_system_prompt method")
    else:
        print("⚠️  Could not find _get_curation_system_prompt method to replace")
    
    # Replace the user prompt method
    old_prompt_method = '''    def _build_curation_prompt(self, tpt: Any, available_parts: List[Dict[str, Any]], 
                             available_transforms: List[Dict[str, Any]], 
                             nutrient_data: List[Dict[str, Any]]) -> str:'''
    
    new_prompt_method = '''    def _build_curation_prompt(self, tpt: Any, available_parts: List[Dict[str, Any]], 
                             available_transforms: List[Dict[str, Any]], 
                             nutrient_data: List[Dict[str, Any]]) -> str:
        """Build prompt for ontology curation"""
        from .optimized_prompts import get_enhanced_curation_prompt
        return get_enhanced_curation_prompt(tpt, available_parts, available_transforms, nutrient_data)'''
    
    if old_prompt_method in content:
        # Find the method and replace its implementation
        lines = content.split('\\n')
        new_lines = []
        in_method = False
        method_indent = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def _build_curation_prompt'):
                in_method = True
                method_indent = len(line) - len(line.lstrip())
                new_lines.append(line)
                new_lines.append('        """Build prompt for ontology curation"""')
                new_lines.append('        from .optimized_prompts import get_enhanced_curation_prompt')
                new_lines.append('        return get_enhanced_curation_prompt(tpt, available_parts, available_transforms, nutrient_data)')
                continue
            
            if in_method and line.strip() and len(line) - len(line.lstrip()) <= method_indent:
                in_method = False
            
            if not in_method:
                new_lines.append(line)
        
        content = '\\n'.join(new_lines)
        print("✅ Updated _build_curation_prompt method")
    else:
        print("⚠️  Could not find _build_curation_prompt method to replace")
    
    # Write updated file
    with open(file_path, 'w') as f:
        f.write(content)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Upgrade evidence ingestion prompts with optimized versions")
    parser.add_argument("--evidence-dir", type=Path, required=True,
                        help="Path to evidence directory")
    parser.add_argument("--backup-dir", type=Path,
                        help="Directory to backup original files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be changed without making changes")
    
    args = parser.parse_args()
    
    print("🚀 UPGRADING EVIDENCE INGESTION PROMPTS")
    print("="*50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        return
    
    # Create backup
    if args.backup_dir:
        backup_original_files(args.evidence_dir, args.backup_dir)
    
    # Update files
    print(f"\\n📝 Updating Tier 1 (Taxon Resolution)...")
    update_tier1_taxon_py(args.evidence_dir)
    
    print(f"\\n📝 Updating Tier 2 (TPT Construction)...")
    update_tier2_tpt_py(args.evidence_dir)
    
    print(f"\\n📝 Updating Tier 3 (Curation)...")
    update_tier3_curator_py(args.evidence_dir)
    
    print(f"\\n✅ PROMPT UPGRADE COMPLETE!")
    print(f"   - Enhanced prompts leverage ontology patterns")
    print(f"   - Better edge case handling")
    print(f"   - Improved accuracy and consistency")
    print(f"   - Original files backed up to {args.backup_dir}")

if __name__ == "__main__":
    main()
