from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

def find_project_root(start: Optional[Path] = None) -> Path:
    """Find project root by walking up directory tree looking for pnpm-workspace.yaml."""
    if start is None:
        start = Path(__file__).parent
    
    cur = start.resolve()
    while True:
        if (cur / "pnpm-workspace.yaml").exists():
            return cur
        if cur.parent == cur:
            return start  # fallback: no marker found
        cur = cur.parent

def load_env(project_root: Optional[Path] = None) -> None:
    """Load environment variables from .env file if it exists."""
    try:
        from dotenv import load_dotenv  # type: ignore
        
        if project_root is None:
            project_root = find_project_root()
        
        dotenv_path = project_root / ".env"
        # Load only if the file exists; do not override existing env vars
        if dotenv_path.exists():
            load_dotenv(dotenv_path, override=False)
    except Exception:
        # If python-dotenv is not installed, the app can still rely on OS env vars.
        pass

def resolve_path(path: str, project_root: Optional[Path] = None) -> Path:
    """Resolve a path relative to project root."""
    if project_root is None:
        project_root = find_project_root()
    
    if Path(path).is_absolute():
        return Path(path)
    else:
        return (project_root / path).resolve()

def get_required_env(key: str, default: Optional[str] = None) -> str:
    """Get required environment variable, raising error if not found."""
    value = os.environ.get(key, default)
    if value is None:
        raise ValueError(f"Required environment variable {key} is not set")
    return value

def get_optional_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get optional environment variable with default value."""
    return os.environ.get(key, default)
