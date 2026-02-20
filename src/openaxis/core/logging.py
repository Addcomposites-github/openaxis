"""
Structured logging configuration for OpenAxis.

Uses structlog (https://www.structlog.org/) to provide structured, context-rich
logging throughout the application. Supports both JSON output (production) and
colored console output (development).

Usage::

    from openaxis.core.logging import configure_logging, get_logger

    configure_logging(json_output=False)  # Call once at startup
    logger = get_logger(__name__)
    logger.info("slicing_complete", layers=42, time_s=1.3)
"""

import logging
import sys
from typing import Optional

import structlog


def configure_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure structured logging for the entire application.

    Call this once at application startup (e.g., in server.py or cli.py).

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: If True, output JSON lines (for production/log aggregation).
                     If False, output colored console-friendly lines (dev mode).
        log_file: Optional path to write logs to a file in addition to stderr.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Standard library logging configuration (for third-party libs)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=handlers,
        force=True,
    )

    # Shared processors for both dev and production
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        # Production: JSON lines to stderr/file
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Development: colored, human-readable console output
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the stdlib formatter to use structlog processors
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    for handler in logging.root.handlers:
        handler.setFormatter(formatter)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structlog logger for the given module name.

    Args:
        name: Module name, typically ``__name__``.

    Returns:
        A bound structlog logger instance.
    """
    return structlog.get_logger(name)
