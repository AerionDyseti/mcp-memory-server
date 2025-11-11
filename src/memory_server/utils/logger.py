"""
Logging utilities for memory server.

Provides structured logging with file and console output.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from memory_server.config import get_settings


def setup_logger(name: str, log_file: Optional[Path] = None) -> logging.Logger:
    """
    Set up a logger with console and optionally file output.

    Args:
        name: Logger name
        log_file: Optional path to log file

    Returns:
        Configured logger instance
    """
    settings = get_settings()
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always log debug to file
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default configuration.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    settings = get_settings()
    log_dir = settings.get_log_dir()
    log_file = log_dir / "memory-server.log"
    return setup_logger(name, log_file)
