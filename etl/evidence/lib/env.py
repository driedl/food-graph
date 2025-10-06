from __future__ import annotations
from pathlib import Path
from lib.config import find_project_root, load_env

# Centralized environment loader. Import this module anywhere early to ensure
# .env variables are loaded for the current process if python-dotenv is present.
# This is now a thin wrapper around the shared config utilities.

# Load environment variables using shared utilities
load_env()


