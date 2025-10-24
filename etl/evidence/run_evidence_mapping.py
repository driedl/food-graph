#!/usr/bin/env python3
"""
Run 3-Tier Evidence Mapping

Simple script to run the new 3-tier evidence mapping system.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Add the etl directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from evidence.evidence_mapper import main

if __name__ == "__main__":
    main()
