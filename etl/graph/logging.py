import logging
from lib.logging import setup_logger as _setup_logger, log as _log

# Re-export shared utilities for backward compatibility
def set_verbosity(verbose: bool) -> None:
    _setup_logger("graph", verbose)

def log() -> logging.Logger:
    return _log()
