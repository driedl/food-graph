import logging, os
from rich.logging import RichHandler

_LOGGER = logging.getLogger("mise")
_HANDLER = RichHandler(rich_tracebacks=True, markup=True)
_FORMAT = "%(message)s"

def set_verbosity(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format=_FORMAT, datefmt="[%X]", handlers=[_HANDLER])

def log() -> logging.Logger:
    return _LOGGER
