import json, subprocess, sys
from pathlib import Path

def _write(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def _write_jsonl(p: Path, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

def _run(cmd):
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def _read_jsonl(p: Path):
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("//"): continue
        out.append(json.loads(s))
    return out

def test_stage_e_hash_is_deterministic(tmp_path):
    in_dir = tmp_path / "onto"
    build = tmp_path / "build"
    # minimal transforms canon with identity-bearing tf:cure
    tcanon = [{
        "id": "tf:cure",
        "identity": True,
        "order": 60,
        "params": [
            {"key": "nitrite_ppm", "kind": "number", "identity_param": True},
            {"key": "salt_pct", "kind": "number", "identity_param": False}
        ]
    }]
    _write(build / "tmp" / "transforms_canon.json", tcanon)
    # minimal seed with unordered path (order shouldn't matter)
    seed = [{
        "taxon_id": "tx:plantae:rosaceae:prunus:domestica",
        "part_id": "part:meat",
        "family_hint": "DRY_CURED_MEAT",
        "path": [{"id": "tf:cure", "params": {"nitrite_ppm": 110}}],
        "path_full": [{"id": "tf:cure", "params": {"nitrite_ppm": 110}}]
    }]
    _write_jsonl(build / "tmp" / "tpt_seed.jsonl", seed)

    # need ontology root for rules/ (may be empty)
    (in_dir / "rules").mkdir(parents=True, exist_ok=True)

    # first run
    rc, out, err = _run([sys.executable, "-m", "mise", "run", "E", "--in", str(in_dir), "--build", str(build)])
    assert rc == 0, err
    out1 = _read_jsonl(build / "tmp" / "tpt_canon.jsonl")
    assert len(out1) == 1
    id1 = out1[0]["id"]; h1 = out1[0]["identity_hash"]

    # run again (no changes)
    rc, out, err = _run([sys.executable, "-m", "mise", "run", "E", "--in", str(in_dir), "--build", str(build)])
    assert rc == 0, err
    out2 = _read_jsonl(build / "tmp" / "tpt_canon.jsonl")
    assert len(out2) == 1
    assert out2[0]["id"] == id1
    assert out2[0]["identity_hash"] == h1

def test_param_buckets_same_bucket_same_hash(tmp_path):
    in_dir = tmp_path / "onto"
    build = tmp_path / "build"
    (in_dir / "rules").mkdir(parents=True, exist_ok=True)
    # Buckets: ≤0 → none, ≤120 → low, else high
    buckets = {"tf:cure.nitrite_ppm": {"cuts": [0, 120], "labels": ["none", "low", "high"]}}
    _write(in_dir / "rules" / "param_buckets.json", buckets)

    tcanon = [{
        "id": "tf:cure",
        "identity": True,
        "order": 60,
        "params": [{"key": "nitrite_ppm", "kind": "number", "identity_param": True}]
    }]
    _write(build / "tmp" / "transforms_canon.json", tcanon)

    # two seeds in the same bucket ("low")
    seed = [
        {
            "taxon_id": "tx:plantae:rosaceae:prunus:domestica",
            "part_id": "part:meat",
            "family_hint": "DRY_CURED_MEAT",
            "path": [{"id": "tf:cure", "params": {"nitrite_ppm": 100}}],
            "path_full": [{"id": "tf:cure", "params": {"nitrite_ppm": 100}}]
        },
        {
            "taxon_id": "tx:plantae:rosaceae:prunus:domestica",
            "part_id": "part:meat",
            "family_hint": "DRY_CURED_MEAT",
            "path": [{"id": "tf:cure", "params": {"nitrite_ppm": 110}}],
            "path_full": [{"id": "tf:cure", "params": {"nitrite_ppm": 110}}]
        }
    ]
    _write_jsonl(build / "tmp" / "tpt_seed.jsonl", seed)

    rc, out, err = _run([sys.executable, "-m", "mise", "run", "E", "--in", str(in_dir), "--build", str(build)])
    assert rc == 0, err
    rows = _read_jsonl(build / "tmp" / "tpt_canon.jsonl")
    # After bucketing, both records should have the same identity signature and be deduplicated
    assert len(rows) == 1
    # The single record should have the bucketed value
    assert rows[0]["identity"][0]["params"]["nitrite_ppm"] == "low"

def test_param_buckets_cross_boundary_changes_hash(tmp_path):
    in_dir = tmp_path / "onto"
    build = tmp_path / "build"
    (in_dir / "rules").mkdir(parents=True, exist_ok=True)
    buckets = {"tf:cure.nitrite_ppm": {"cuts": [0, 120], "labels": ["none", "low", "high"]}}
    _write(in_dir / "rules" / "param_buckets.json", buckets)

    tcanon = [{
        "id": "tf:cure",
        "identity": True,
        "order": 60,
        "params": [{"key": "nitrite_ppm", "kind": "number", "identity_param": True}]
    }]
    _write(build / "tmp" / "transforms_canon.json", tcanon)

    seed = [
        {
            "taxon_id": "tx:plantae:rosaceae:prunus:domestica",
            "part_id": "part:meat",
            "family_hint": "DRY_CURED_MEAT",
            "path": [{"id": "tf:cure", "params": {"nitrite_ppm": 110}}],  # → "low"
            "path_full": [{"id": "tf:cure", "params": {"nitrite_ppm": 110}}]
        },
        {
            "taxon_id": "tx:plantae:rosaceae:prunus:domestica",
            "part_id": "part:meat",
            "family_hint": "DRY_CURED_MEAT",
            "path": [{"id": "tf:cure", "params": {"nitrite_ppm": 130}}],  # → "high"
            "path_full": [{"id": "tf:cure", "params": {"nitrite_ppm": 130}}]
        }
    ]
    _write_jsonl(build / "tmp" / "tpt_seed.jsonl", seed)

    rc, out, err = _run([sys.executable, "-m", "mise", "run", "E", "--in", str(in_dir), "--build", str(build)])
    assert rc == 0, err
    rows = _read_jsonl(build / "tmp" / "tpt_canon.jsonl")
    assert len(rows) == 2
    # crossing bucket boundary should change hash
    assert rows[0]["identity_hash"] != rows[1]["identity_hash"]
