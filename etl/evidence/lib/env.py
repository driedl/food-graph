from __future__ import annotations
from pathlib import Path

# Centralized environment loader. Import this module anywhere early to ensure
# .env variables are loaded for the current process if python-dotenv is present.
try:
    from dotenv import load_dotenv  # type: ignore

    # Find project root by walking up from this file until we find pnpm-workspace.yaml
    def _find_project_root(start: Path) -> Path:
        cur = start.resolve()
        while True:
            if (cur / "pnpm-workspace.yaml").exists():
                return cur
            if cur.parent == cur:
                return start  # fallback: no marker found
            cur = cur.parent

    project_root = _find_project_root(Path(__file__).parent)
    dotenv_path = project_root / ".env"
    # Load only if the file exists; do not override existing env vars
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=False)
except Exception:
    # If python-dotenv is not installed, the app can still rely on OS env vars.
    pass


