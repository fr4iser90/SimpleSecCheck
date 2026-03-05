"""Backend logging configuration."""

from __future__ import annotations

import logging
import os

DEFAULT_LOG_LEVEL = "INFO"


def get_log_level() -> str:
    """Return the configured log level (defaults to INFO)."""
    return os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()


def setup_logging() -> str:
    """Configure root logging and tune common loggers."""
    level_name = get_log_level()
    level = logging.getLevelName(level_name)
    if isinstance(level, str):
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)

    access_level = level if level == logging.DEBUG else logging.WARNING
    logging.getLogger("uvicorn.access").setLevel(access_level)

    return level_name