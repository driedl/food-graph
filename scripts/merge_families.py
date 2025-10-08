#!/usr/bin/env python3
"""
Script to merge all JSONL files from the plantae/families folder into a single file.
"""

import os
import json
import glob
from pathlib import Path

def merge_families_jsonl():
    """Merge all JSONL files from families folder into a single file."""
    
    # Define paths
    families_dir = "/Users/daveriedl/git/food-graph/data/ontology/taxa/plantae/families"
    output_file = "/Users/daveriedl/git/food-graph/data/ontology/taxa/plantae/families_merged.jsonl"
    
    # Find all JSONL files in the families directory
    jsonl_files = glob.glob(os.path.join(families_dir, "*.jsonl"))
    
    print(f"Found {len(jsonl_files)} JSONL files to merge:")
    for file in sorted(jsonl_files):
        print(f"  - {os.path.basename(file)}")
    
    # Merge all JSONL files
    total_lines = 0
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for jsonl_file in sorted(jsonl_files):
            print(f"Processing {os.path.basename(jsonl_file)}...")
            with open(jsonl_file, 'r', encoding='utf-8') as infile:
                for line in infile:
                    line = line.strip()
                    if line:  # Skip empty lines
                        # Validate JSON before writing
                        try:
                            json.loads(line)
                            outfile.write(line + '\n')
                            total_lines += 1
                        except json.JSONDecodeError as e:
                            print(f"  Warning: Invalid JSON in {jsonl_file}: {line[:50]}...")
    
    print(f"\nMerged {total_lines} lines from {len(jsonl_files)} files into {output_file}")
    return output_file, total_lines

if __name__ == "__main__":
    output_file, line_count = merge_families_jsonl()
    print(f"✅ Successfully created merged file: {output_file}")
    print(f"📊 Total lines merged: {line_count}")
