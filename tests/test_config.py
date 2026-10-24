from pathlib import Path

import pytest

from app.config import AppConfig, ConfigurationError


def test_config_defaults():
    config = AppConfig.from_environment(environ={})

    assert config.history_csv_path == Path("calculator_history.csv")
    assert config.autosave_history is True
    assert config.log_level == "INFO"
    assert config.log_file_path == Path("calculator.log")
    assert config.history_dir == Path(".")
    assert config.log_dir == Path(".")
    assert config.max_history_size == 1000
    assert config.precision == 10
    assert config.max_input_value == 1e308
    assert config.default_encoding == "utf-8"


def test_config_reads_and_validates_environment_values():
    config = AppConfig.from_environment(
        environ={
            "CALCULATOR_HISTORY_FILE": "~/data/history.CSV",
            "CALCULATOR_AUTOSAVE_HISTORY": "off",
            "CALCULATOR_LOG_LEVEL": "debug",
            "CALCULATOR_LOG_FILE": "~/logs/calculator.log",
            "CALCULATOR_LOG_DIR": "~/logs",
            "CALCULATOR_HISTORY_DIR": "~/history",
            "CALCULATOR_AUTO_SAVE": "no",
            "CALCULATOR_MAX_HISTORY_SIZE": "25",
            "CALCULATOR_PRECISION": "4",
            "CALCULATOR_MAX_INPUT_VALUE": "5000",
            "CALCULATOR_DEFAULT_ENCODING": "cp1252",
        }
    )

    assert config.history_csv_path == Path("~/data/history.CSV").expanduser()
    assert config.autosave_history is False
    assert config.log_level == "DEBUG"
    assert config.log_file_path == Path("~/logs/calculator.log").expanduser()
    assert config.log_dir == Path("~/logs").expanduser()
    assert config.history_dir == Path("~/history").expanduser()
    assert config.max_history_size == 25
    assert config.precision == 4
    assert config.max_input_value == 5000
    assert config.default_encoding == "cp1252"


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"CALCULATOR_HISTORY_FILE": " "}, "non-empty path"),
        ({"CALCULATOR_HISTORY_FILE": "history.json"}, ".csv extension"),
        ({"CALCULATOR_AUTOSAVE_HISTORY": "sometimes"}, "must be true or false"),
        ({"CALCULATOR_LOG_LEVEL": "TRACE"}, "CALCULATOR_LOG_LEVEL"),
        ({"CALCULATOR_LOG_FILE": " "}, "non-empty path"),
        ({"CALCULATOR_LOG_DIR": " "}, "CALCULATOR_LOG_DIR"),
        ({"CALCULATOR_HISTORY_DIR": " "}, "CALCULATOR_HISTORY_DIR"),
        ({"CALCULATOR_MAX_HISTORY_SIZE": "0"}, "at least 1"),
        ({"CALCULATOR_MAX_HISTORY_SIZE": "many"}, "must be an integer"),
        ({"CALCULATOR_PRECISION": "-1"}, "between 0 and 15"),
        ({"CALCULATOR_PRECISION": "16"}, "between 0 and 15"),
        ({"CALCULATOR_PRECISION": "2.5"}, "must be an integer"),
        ({"CALCULATOR_MAX_INPUT_VALUE": "nan"}, "positive finite number"),
        ({"CALCULATOR_MAX_INPUT_VALUE": "0"}, "positive finite number"),
        ({"CALCULATOR_MAX_INPUT_VALUE": "large"}, "positive finite number"),
        ({"CALCULATOR_DEFAULT_ENCODING": "not-a-codec"}, "supported encoding"),
        ({"CALCULATOR_DEFAULT_ENCODING": " "}, "supported encoding"),
    ],
)
def test_config_rejects_invalid_settings(settings, message):
    with pytest.raises(ConfigurationError, match=message):
        AppConfig.from_environment(environ=settings)


def test_config_loads_values_from_dotenv_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dotenv_file = tmp_path / ".env.test"
    dotenv_file.write_text(
        "CALCULATOR_HISTORY_FILE=from-dotenv.csv\n"
        "CALCULATOR_AUTOSAVE_HISTORY=no\n"
        "CALCULATOR_LOG_LEVEL=WARNING\n"
        "CALCULATOR_LOG_FILE=from-dotenv.log\n"
        "CALCULATOR_LOG_DIR=dotenv-logs\n"
        "CALCULATOR_HISTORY_DIR=dotenv-history\n"
        "CALCULATOR_MAX_HISTORY_SIZE=8\n"
        "CALCULATOR_AUTO_SAVE=false\n"
        "CALCULATOR_PRECISION=3\n"
        "CALCULATOR_MAX_INPUT_VALUE=250\n"
        "CALCULATOR_DEFAULT_ENCODING=cp1252\n",
        encoding="utf-8",
    )
    for key in (
        "CALCULATOR_HISTORY_FILE",
        "CALCULATOR_AUTOSAVE_HISTORY",
        "CALCULATOR_LOG_LEVEL",
        "CALCULATOR_LOG_FILE",
        "CALCULATOR_AUTO_SAVE",
        "CALCULATOR_LOG_DIR",
        "CALCULATOR_HISTORY_DIR",
        "CALCULATOR_MAX_HISTORY_SIZE",
        "CALCULATOR_PRECISION",
        "CALCULATOR_MAX_INPUT_VALUE",
        "CALCULATOR_DEFAULT_ENCODING",
    ):
        monkeypatch.delenv(key, raising=False)

    config = AppConfig.from_environment(dotenv_path=dotenv_file)

    assert config.history_csv_path == Path("dotenv-history/from-dotenv.csv")
    assert config.autosave_history is False
    assert config.log_level == "WARNING"
    assert config.log_file_path == Path("dotenv-logs/from-dotenv.log")
    assert config.max_history_size == 8
    assert config.precision == 3
    assert config.max_input_value == 250
    assert config.default_encoding == "cp1252"


def test_config_resolves_relative_files_under_configured_directories():
    config = AppConfig.from_environment(
        environ={
            "CALCULATOR_LOG_DIR": "logs",
            "CALCULATOR_HISTORY_DIR": "history",
        }
    )

    assert config.log_file_path == Path("logs/calculator.log")
    assert config.history_csv_path == Path("history/calculator_history.csv")


def test_new_auto_save_setting_takes_precedence_over_legacy_setting():
    config = AppConfig.from_environment(
        environ={
            "CALCULATOR_AUTO_SAVE": "false",
            "CALCULATOR_AUTOSAVE_HISTORY": "true",
        }
    )

    assert config.autosave_history is False


def test_config_keeps_absolute_file_paths_outside_base_directories(tmp_path):
    history_path = tmp_path / "history.csv"
    log_path = tmp_path / "calculator.log"
    config = AppConfig.from_environment(
        environ={
            "CALCULATOR_HISTORY_DIR": "history",
            "CALCULATOR_HISTORY_FILE": str(history_path),
            "CALCULATOR_LOG_DIR": "logs",
            "CALCULATOR_LOG_FILE": str(log_path),
        }
    )

    assert config.history_csv_path == history_path
    assert config.log_file_path == log_path


def test_environment_values_override_dotenv_file(tmp_path, monkeypatch):
    dotenv_file = tmp_path / ".env.test"
    dotenv_file.write_text("CALCULATOR_LOG_LEVEL=DEBUG\n", encoding="utf-8")
    monkeypatch.setenv("CALCULATOR_LOG_LEVEL", "ERROR")

    config = AppConfig.from_environment(dotenv_path=dotenv_file)

    assert config.log_level == "ERROR"
