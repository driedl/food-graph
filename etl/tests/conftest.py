"""Pytest configuration and fixtures for ETL2 tests"""
import tempfile
from pathlib import Path
import pytest

@pytest.fixture
def temp_build_dir():
    """Create a temporary build directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def temp_ontology_dir():
    """Create a temporary ontology directory with minimal test data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        ontology_dir = Path(tmpdir)
        
        # Create minimal test structure
        (ontology_dir / "taxa").mkdir()
        (ontology_dir / "rules").mkdir()
        
        # Create minimal taxa index
        taxa_index = ontology_dir / "taxa" / "index.jsonl"
        taxa_index.write_text(
            '{"id":"tx:life","rank":"kingdom","display_name":"Life","latin_name":"Life"}\n'
            '{"id":"tx:eukaryota","parent":"tx:life","rank":"kingdom","display_name":"Eukaryotes","latin_name":"Eukaryota"}\n'
            '{"id":"tx:plantae","parent":"tx:eukaryota","rank":"kingdom","display_name":"Plants","latin_name":"Plantae"}\n'
        )
        # minimal transforms so Stage A can run cleanly
        (ontology_dir / "transforms.json").write_text('''[
  {
    "id": "tf:cook",
    "name": "Cook",
    "identity": true,
    "order": 90,
    "params": [
      {
        "key": "method",
        "kind": "enum",
        "enum": ["raw", "boil", "steam", "bake", "roast", "fry", "broil"]
      },
      {
        "key": "fat_added",
        "kind": "boolean"
      }
    ],
    "notes": "Thermal processing"
  },
  {
    "id": "tf:brine",
    "name": "Brine/Can (Salt)",
    "identity": true,
    "order": 30,
    "params": [
      {
        "key": "salt_level",
        "kind": "enum",
        "enum": ["none", "light", "medium", "heavy"]
      }
    ],
    "notes": "Salt preservation"
  }
]''')
        
        # Create minimal parts
        parts_file = ontology_dir / "parts.json"
        parts_file.write_text('''[{"id": "part:fruit", "name": "Fruit"}, {"id": "part:leaf", "name": "Leaf"}]''')
        
        # Create minimal attributes
        attributes_file = ontology_dir / "attributes.json"
        attributes_file.write_text('''[{"id": "attr:color", "name": "Color"}]''')
        
        # Create minimal nutrients
        nutrients_file = ontology_dir / "nutrients.json"
        nutrients_file.write_text('''[{"id": "nut:protein", "name": "Protein"}]''')
        
        yield ontology_dir
