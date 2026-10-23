"""Environment and dotenv-backed application configuration."""

import codecs
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
    log_file_path: Path = Path("calculator.log")
    log_dir: Path = Path(".")
    history_dir: Path = Path(".")
    max_history_size: int = 1000
    precision: int = 10
    max_input_value: float = 1e308
    default_encoding: str = "utf-8"

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

        raw_history_dir = settings.get("CALCULATOR_HISTORY_DIR", ".").strip()
        if not raw_history_dir:
            raise ConfigurationError(
                "CALCULATOR_HISTORY_DIR must be a non-empty path."
            )
        history_dir = Path(raw_history_dir).expanduser()

        raw_log_dir = settings.get("CALCULATOR_LOG_DIR", ".").strip()
        if not raw_log_dir:
            raise ConfigurationError("CALCULATOR_LOG_DIR must be a non-empty path.")
        log_dir = Path(raw_log_dir).expanduser()

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
        history_path = _resolve_configured_path(history_path, history_dir)

        raw_autosave = settings.get(
            "CALCULATOR_AUTO_SAVE",
            settings.get("CALCULATOR_AUTOSAVE_HISTORY", "true"),
        ).strip().lower()
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
                "CALCULATOR_AUTO_SAVE must be true or false."
            )

        log_level = settings.get("CALCULATOR_LOG_LEVEL", "INFO").strip().upper()
        if log_level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ConfigurationError(
                "CALCULATOR_LOG_LEVEL must be CRITICAL, ERROR, WARNING, INFO, or DEBUG."
            )

        raw_log_file_path = settings.get(
            "CALCULATOR_LOG_FILE", "calculator.log"
        ).strip()
        if not raw_log_file_path:
            raise ConfigurationError(
                "CALCULATOR_LOG_FILE must be a non-empty path."
            )
        log_file_path = _resolve_configured_path(
            Path(raw_log_file_path).expanduser(), log_dir
        )

        max_history_size = _parse_integer_setting(
            settings, "CALCULATOR_MAX_HISTORY_SIZE", 1000, minimum=1
        )
        precision = _parse_integer_setting(
            settings, "CALCULATOR_PRECISION", 10, minimum=0, maximum=15
        )
        raw_max_input_value = settings.get(
            "CALCULATOR_MAX_INPUT_VALUE", "1e308"
        ).strip()
        try:
            max_input_value = float(raw_max_input_value)
        except ValueError as exc:
            raise ConfigurationError(
                "CALCULATOR_MAX_INPUT_VALUE must be a positive finite number."
            ) from exc
        if not 0 < max_input_value < float("inf"):
            raise ConfigurationError(
                "CALCULATOR_MAX_INPUT_VALUE must be a positive finite number."
            )

        default_encoding = settings.get(
            "CALCULATOR_DEFAULT_ENCODING", "utf-8"
        ).strip()
        if not default_encoding:
            raise ConfigurationError(
                "CALCULATOR_DEFAULT_ENCODING must be a supported encoding."
            )
        try:
            codecs.lookup(default_encoding)
        except LookupError as exc:
            raise ConfigurationError(
                "CALCULATOR_DEFAULT_ENCODING must be a supported encoding."
            ) from exc

        return cls(
            history_csv_path=history_path,
            autosave_history=boolean_values[raw_autosave],
            log_level=log_level,
            log_file_path=log_file_path,
            log_dir=log_dir,
            history_dir=history_dir,
            max_history_size=max_history_size,
            precision=precision,
            max_input_value=max_input_value,
            default_encoding=default_encoding,
        )


def _resolve_configured_path(path: Path, base_directory: Path) -> Path:
    """Resolve relative filenames under their configured base directory."""
    return path if path.is_absolute() else base_directory / path


def _parse_integer_setting(
    settings: Mapping[str, str],
    name: str,
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> int:
    """Parse and validate an integer configuration value."""
    raw_value = settings.get(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc
    if value < minimum or (maximum is not None and value > maximum):
        range_description = (
            f"between {minimum} and {maximum}"
            if maximum is not None
            else f"at least {minimum}"
        )
        raise ConfigurationError(f"{name} must be {range_description}.")
    return value
