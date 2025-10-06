import subprocess, sys
from pathlib import Path

def test_smoke_build(tmp_path, monkeypatch):
    build_dir = tmp_path / "build"
    in_dir = tmp_path / "ontology"
    in_dir.mkdir(parents=True)
    (in_dir / "taxa").mkdir()
    (in_dir / "rules").mkdir()

    # minimal taxa (see conftest improvements below if you prefer fixtures)
    (in_dir / "taxa" / "index.jsonl").write_text(
        '{"id":"tx:life","rank":"kingdom","display_name":"Life","latin_name":"Life"}\n'
        '{"id":"tx:eukaryota","parent":"tx:life","rank":"kingdom","display_name":"Eukaryotes","latin_name":"Eukaryota"}\n'
        '{"id":"tx:plantae","parent":"tx:eukaryota","rank":"kingdom","display_name":"Plants","latin_name":"Plantae"}\n'
    )
    (in_dir / "parts.json").write_text('[{"id":"part:fruit","name":"Fruit"}]')
    (in_dir / "attributes.json").write_text('[{"id":"attr:color","name":"Color"}]')
    (in_dir / "nutrients.json").write_text('[{"id":"nut:protein","name":"Protein"}]')
    (in_dir / "transforms.json").write_text('''[
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

    result = subprocess.run(
        [sys.executable, "-m", "graph", "run", "build", "--in", str(in_dir), "--build", str(build_dir), "--with-tests"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert (build_dir / "compiled" / "taxa.jsonl").exists()
    assert (build_dir / "compiled" / "docs.jsonl").exists()
    assert (build_dir / "report" / "verify_stage_0.json").exists()
    assert (build_dir / "report" / "verify_stage_a.json").exists()
    assert (build_dir / "report" / "verify_stage_b.json").exists()
    assert (build_dir / "report" / "verify_stage_c.json").exists()
