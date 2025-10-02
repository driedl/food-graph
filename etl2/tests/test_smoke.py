import json, subprocess, sys, os, pathlib

def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr

def test_mise_plan_and_run(tmp_path, monkeypatch):
    # run inside a temp build root
    monkeypatch.setenv("GRAPH_BUILD_ROOT", str(tmp_path / "build"))
    code, out, err = run([sys.executable, "-m", "mise", "plan"])
    assert code == 0
    code, out, err = run([sys.executable, "-m", "mise", "run", "--only", "HELLO"])
    assert code == 0
    summary = json.loads(out)
    assert summary["success"] is True
    assert any(s["id"] == "HELLO" for s in summary["stages"])
    # artifact exists
    hello = tmp_path / "build" / "out" / "hello.json"
    assert hello.exists(), "hello.json should be produced"
    data = json.loads(hello.read_text())
    assert data["message"] == "mise says hello"
