"""Logging configuration for the calculator application."""

import logging


def configure_logging(log_level: str) -> None:
    """Configure the root logger using a validated logging level."""
    logging.basicConfig(level=getattr(logging, log_level))
