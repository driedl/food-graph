from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional
from .io import expand_globs, hash_of_files, write_json
from .logging import log
from .config import BuildConfig
import inspect, hashlib, time

@dataclass
class Stage:
    id: str
    name: str
    inputs: List[str] = field(default_factory=list)   # globs
    outputs: List[Path] = field(default_factory=list) # concrete paths
    run: Callable[["Context"], None] = lambda ctx: None

    # computed at plan() time
    cache_hit: bool = False
    fingerprint: Optional[str] = None

@dataclass
class Context:
    cfg: BuildConfig
    now: float

    def write_report(self, stage: Stage, status: str, extra: Dict = None):
        out = {
            "stage": stage.id,
            "name": stage.name,
            "status": status,
            "duration_ms": round((time.time() - self.now) * 1000, 1),
            "fingerprint": stage.fingerprint,
        }
        if extra:
            out.update(extra)
        write_json(self.cfg.build_root / "report" / "stages" / f"{stage.id}.json", out)

class Dag:
    def __init__(self, stages: List[Stage], cfg: BuildConfig):
        self.stages = stages
        self.cfg = cfg
        (self.cfg.build_root / "report" / "stages").mkdir(parents=True, exist_ok=True)
        (self.cfg.build_root / "report" / ".cache").mkdir(parents=True, exist_ok=True)

    def plan(self) -> List[Stage]:
        for s in self.stages:
            code_hash = hashlib.sha1(inspect.getsource(s.run).encode()).hexdigest()
            inputs = expand_globs(s.inputs)
            input_hash = hash_of_files(inputs) if inputs else "no-inputs"
            fp = hashlib.sha1(f"{code_hash}|{input_hash}".encode()).hexdigest()
            s.fingerprint = fp
            cache_file = self.cfg.build_root / "report" / ".cache" / f"{s.id}.json"
            s.cache_hit = cache_file.exists() and cache_file.read_text() == fp
        return self.stages

    def save_cache(self, s: Stage):
        cache_file = self.cfg.build_root / "report" / ".cache" / f"{s.id}.json"
        cache_file.write_text(s.fingerprint or "", encoding="utf-8")

class StageRegistry:
    @staticmethod
    def load_default(cfg: BuildConfig) -> Dag:
        # Import here to allow stages to import registry without cycles
        from .stages.hello import HelloStage
        stages: List[Stage] = [
            HelloStage(cfg),
        ]
        return Dag(stages, cfg)

class DagRunner:
    def __init__(self, cfg: BuildConfig, dag: Dag, ignore_cache: bool = False):
        self.cfg = cfg
        self.dag = dag
        self.ignore_cache = ignore_cache

    def run(self, only: str = None, start: str = None, end: str = None) -> Dict:
        plan = self.dag.plan()
        ids = [s.id for s in plan]

        def in_slice(sid: str) -> bool:
            if only:
                return sid == only
            if start and ids.index(sid) < ids.index(start):
                return False
            if end and ids.index(sid) > ids.index(end):
                return False
            return True

        summary = {"success": True, "stages": [], "built_at": int(time.time())}
        for s in plan:
            if not in_slice(s.id):
                continue
            ctx = Context(self.cfg, now=time.time())
            try:
                if (s.cache_hit and not self.ignore_cache):
                    ctx.write_report(s, "skipped", {"cached": True})
                    summary["stages"].append({"id": s.id, "status": "skipped"})
                    continue
                s.run(ctx)
                self.dag.save_cache(s)
                ctx.write_report(s, "ok", {"cached": False})
                summary["stages"].append({"id": s.id, "status": "ok"})
            except Exception as e:
                ctx.write_report(s, "error", {"error": str(e)})
                summary["success"] = False
                summary["stages"].append({"id": s.id, "status": "error", "error": str(e)})
                break
        # Write top-level run report
        write_json(self.cfg.build_root / "report" / "run.json", summary)
        return summary
