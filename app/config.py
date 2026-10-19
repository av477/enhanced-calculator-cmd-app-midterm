"""Environment and dotenv-backed application configuration."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Raised when an application setting is invalid."""


@dataclass(frozen=True)
class AppConfig:
    """Validated runtime settings for the calculator application."""

    history_csv_path: Path
    autosave_history: bool
    log_level: str

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
        dotenv_path: str | Path | None = None,
    ) -> "AppConfig":
        """Load dotenv defaults, then validate settings from the environment."""
        if environ is None:
            load_dotenv(
                dotenv_path=Path(dotenv_path) if dotenv_path is not None else None,
                override=False,
            )
            settings = os.environ
        else:
            settings = environ

        raw_history_path = settings.get(
            "CALCULATOR_HISTORY_FILE", "calculator_history.csv"
        ).strip()
        if not raw_history_path:
            raise ConfigurationError(
                "CALCULATOR_HISTORY_FILE must be a non-empty path."
            )
        history_path = Path(raw_history_path).expanduser()
        if history_path.suffix.lower() != ".csv":
            raise ConfigurationError(
                "CALCULATOR_HISTORY_FILE must have a .csv extension."
            )

        raw_autosave = (
            settings.get("CALCULATOR_AUTOSAVE_HISTORY", "true").strip().lower()
        )
        boolean_values = {
            "true": True,
            "1": True,
            "yes": True,
            "on": True,
            "false": False,
            "0": False,
            "no": False,
            "off": False,
        }
        if raw_autosave not in boolean_values:
            raise ConfigurationError(
                "CALCULATOR_AUTOSAVE_HISTORY must be true or false."
            )

        log_level = settings.get("CALCULATOR_LOG_LEVEL", "INFO").strip().upper()
        if log_level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ConfigurationError(
                "CALCULATOR_LOG_LEVEL must be CRITICAL, ERROR, WARNING, INFO, or DEBUG."
            )

        return cls(
            history_csv_path=history_path,
            autosave_history=boolean_values[raw_autosave],
            log_level=log_level,
        )
