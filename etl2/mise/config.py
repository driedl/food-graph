from __future__ import annotations
import os, json, shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

DEFAULT_BUILD_ROOT = "etl2/build"

@dataclass
class BuildConfig:
    build_root: Path
    db_path: Path
    profile: str

    @staticmethod
    def from_env() -> "BuildConfig":
        # If GRAPH_BUILD_ROOT is not set, use absolute path from current working directory
        if "GRAPH_BUILD_ROOT" in os.environ:
            root = Path(os.environ["GRAPH_BUILD_ROOT"])
        else:
            # Find the project root by looking for pnpm-workspace.yaml
            current_dir = Path.cwd()
            project_root = current_dir
            while project_root != project_root.parent:
                if (project_root / "pnpm-workspace.yaml").exists():
                    break
                project_root = project_root.parent
            root = project_root / DEFAULT_BUILD_ROOT
        
        db = Path(os.environ.get("GRAPH_DB_PATH", str(root / "database" / "graph.dev.sqlite")))
        profile = os.environ.get("GRAPH_BUILD_PROFILE", "local")
        cfg = BuildConfig(build_root=root, db_path=db, profile=profile)
        cfg.ensure_dirs()
        return cfg

    def ensure_dirs(self) -> None:
        # Create expected directories
        for p in [
            self.build_root,
            self.build_root / "out",
            self.build_root / "graph",
            self.build_root / "tmp",
            self.build_root / "report" / ".cache",
            self.db_path.parent,
        ]:
            p.mkdir(parents=True, exist_ok=True)

    def as_paths(self) -> Dict[str, str]:
        return {
            "build_root": str(self.build_root),
            "out_dir": str(self.build_root / "out"),
            "graph_dir": str(self.build_root / "graph"),
            "tmp_dir": str(self.build_root / "tmp"),
            "report_dir": str(self.build_root / "report"),
            "cache_dir": str(self.build_root / "report" / ".cache"),
            "database": str(self.db_path),
            "profile": self.profile,
        }

    def clean(self, hard: bool = False) -> None:
        out = self.build_root
        if out.exists():
            shutil.rmtree(out)
        if hard and self.db_path.exists():
            try:
                self.db_path.unlink()
            except FileNotFoundError:
                pass
        # Recreate base folders
        self.ensure_dirs()
