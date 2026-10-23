"""Logging configuration for the calculator application."""

import logging
from pathlib import Path

_LOGGER_NAME = "app.calculator_observers"
_file_handler: logging.FileHandler | None = None
_file_encoding: str | None = None


def configure_logging(
    log_level: str,
    log_file_path: str | Path = "calculator.log",
    encoding: str = "utf-8",
) -> None:
    """Write calculator observer messages to the configured log file."""
    global _file_encoding, _file_handler

    logger = logging.getLogger(_LOGGER_NAME)
    level = getattr(logging, log_level)
    logger.setLevel(level)

    path = Path(log_file_path)
    if (
        _file_handler is not None
        and Path(_file_handler.baseFilename) == path.resolve()
        and _file_encoding == encoding
    ):
        _file_handler.setLevel(level)
        return

    if _file_handler is not None:
        logger.removeHandler(_file_handler)
        _file_handler.close()

    path.parent.mkdir(parents=True, exist_ok=True)
    _file_handler = logging.FileHandler(path, encoding=encoding)
    _file_handler.setLevel(level)
    _file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(_file_handler)
    _file_encoding = encoding
