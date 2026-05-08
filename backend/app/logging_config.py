"""Centralised logging setup.

Wired from `create_app()` so every entry point (uvicorn, pytest, scripts) gets a
consistent root logger configuration. Calling `configure_logging()` more than
once is a no-op so re-imports during tests do not stack handlers.
"""

from __future__ import annotations

import logging
import sys
from logging.config import dictConfig

from app.config import Settings

_CONFIGURED = False


def configure_logging(settings: Settings) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = "DEBUG" if settings.debug else "INFO"
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        if settings.is_development
        else '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    )

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": log_format,
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "default",
                    "level": level,
                },
            },
            "root": {
                "handlers": ["stdout"],
                "level": level,
            },
            # Keep uvicorn's access log readable but route it through our root.
            "loggers": {
                "uvicorn": {"level": level, "handlers": [], "propagate": True},
                "uvicorn.error": {"level": level, "handlers": [], "propagate": True},
                "uvicorn.access": {"level": "WARNING", "handlers": [], "propagate": True},
            },
        }
    )

    _CONFIGURED = True
    logging.getLogger(__name__).debug(
        "Logging configured | level=%s | env=%s", level, settings.app_env
    )
