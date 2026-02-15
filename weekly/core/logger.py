"""
Logging configuration for Weekly.
"""
import logging
import sys
from typing import Optional

from rich.logging import RichHandler


def get_logger(name: str = "weekly") -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Name of the logger

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Use RichHandler for beautiful console logging
        handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=False,
            show_path=False
        )
        
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger


def set_log_level(level: str) -> None:
    """
    Set the log level for the root weekly logger.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logger = logging.getLogger("weekly")
    numeric_level = getattr(logging, level.upper(), None)
    if isinstance(numeric_level, int):
        logger.setLevel(numeric_level)
