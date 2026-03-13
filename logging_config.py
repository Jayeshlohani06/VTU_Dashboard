"""
Centralized logging configuration for VTU Dashboard.
Provides structured logging with console output.
"""

import logging
import os
import time

# Custom formatter with timestamps
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level=None):
    """Initialize logging for the entire application."""
    log_level = level or os.environ.get("LOG_LEVEL", "INFO").upper()

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level, logging.INFO))

    # Avoid duplicate handlers on reload
    if root.handlers:
        return root

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    # Suppress noisy third-party loggers
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    root.info("Logging initialized - level=%s, output=console", log_level)
    return root


def get_logger(name):
    """Get a named logger for a module."""
    return logging.getLogger(name)


# Timing decorator for performance monitoring
class TimingContext:
    """Context manager to log execution time of a block."""

    def __init__(self, logger, operation_name):
        self.logger = logger
        self.operation_name = operation_name

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        elapsed_ms = (time.perf_counter() - self.start) * 1000
        self.logger.info("%s completed in %.1f ms", self.operation_name, elapsed_ms)
