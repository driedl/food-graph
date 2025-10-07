from __future__ import annotations
import logging, os, time
from pathlib import Path
from typing import Dict, Any, Optional, List
from rich.logging import RichHandler
from rich.console import Console

_LOGGER = logging.getLogger("etl")
_HANDLER = RichHandler(rich_tracebacks=True, markup=True)
_FORMAT = "%(message)s"
_CONSOLE = Console()

def setup_logger(name: str = "etl", verbose: bool = False) -> logging.Logger:
    """Setup logger with Rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format=_FORMAT, datefmt="[%X]", handlers=[_HANDLER])
    return logging.getLogger(name)

def log() -> logging.Logger:
    """Get the default ETL logger."""
    return _LOGGER

def console() -> Console:
    """Get the Rich console for styled output."""
    return _CONSOLE

class ProgressTracker:
    """Track progress of ETL operations with timing and metrics."""
    
    def __init__(self, total: int = 0, name: str = "operation"):
        self.total = total
        self.name = name
        self.processed = 0
        self.start_time = time.time()
        self.timings: List[float] = []
        self.metrics: Dict[str, Any] = {}
    
    def update(self, count: int = 1, **metrics) -> None:
        """Update progress and metrics."""
        self.processed += count
        self.timings.append(time.time() - self.start_time)
        self.metrics.update(metrics)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        elapsed = time.time() - self.start_time
        avg_time = sum(self.timings) / len(self.timings) if self.timings else 0
        
        return {
            "processed": self.processed,
            "total": self.total,
            "elapsed": elapsed,
            "avg_time": avg_time,
            "rate": self.processed / elapsed if elapsed > 0 else 0,
            "metrics": self.metrics
        }
    
    def log_progress(self, logger: Optional[logging.Logger] = None) -> None:
        """Log current progress."""
        stats = self.get_stats()
        logger = logger or log()
        
        if self.total > 0:
            pct = (self.processed / self.total) * 100
            logger.info(f"{self.name}: {self.processed}/{self.total} ({pct:.1f}%) - {stats['elapsed']:.1f}s")
        else:
            logger.info(f"{self.name}: {self.processed} items - {stats['elapsed']:.1f}s")

class MetricsCollector:
    """Collect and aggregate metrics from ETL operations."""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self.counters: Dict[str, int] = {}
        self.timings: Dict[str, List[float]] = {}
    
    def increment(self, key: str, value: int = 1) -> None:
        """Increment a counter."""
        self.counters[key] = self.counters.get(key, 0) + value
    
    def set_metric(self, key: str, value: Any) -> None:
        """Set a metric value."""
        self.metrics[key] = value
    
    def add_timing(self, key: str, duration: float) -> None:
        """Add a timing measurement."""
        if key not in self.timings:
            self.timings[key] = []
        self.timings[key].append(duration)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        summary = {
            "counters": self.counters.copy(),
            "metrics": self.metrics.copy(),
            "timings": {}
        }
        
        for key, times in self.timings.items():
            if times:
                summary["timings"][key] = {
                    "count": len(times),
                    "total": sum(times),
                    "avg": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times)
                }
        
        return summary
