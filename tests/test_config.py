from pathlib import Path

import pytest

from app.config import AppConfig, ConfigurationError


def test_config_defaults():
    config = AppConfig.from_environment(environ={})

    assert config.history_csv_path == Path("calculator_history.csv")
    assert config.autosave_history is True
    assert config.log_level == "INFO"


def test_config_reads_and_validates_environment_values():
    config = AppConfig.from_environment(
        environ={
            "CALCULATOR_HISTORY_FILE": "~/data/history.CSV",
            "CALCULATOR_AUTOSAVE_HISTORY": "off",
            "CALCULATOR_LOG_LEVEL": "debug",
        }
    )

    assert config.history_csv_path == Path("~/data/history.CSV").expanduser()
    assert config.autosave_history is False
    assert config.log_level == "DEBUG"


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"CALCULATOR_HISTORY_FILE": " "}, "non-empty path"),
        ({"CALCULATOR_HISTORY_FILE": "history.json"}, ".csv extension"),
        ({"CALCULATOR_AUTOSAVE_HISTORY": "sometimes"}, "must be true or false"),
        ({"CALCULATOR_LOG_LEVEL": "TRACE"}, "CALCULATOR_LOG_LEVEL"),
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
        "CALCULATOR_LOG_LEVEL=WARNING\n",
        encoding="utf-8",
    )
    for key in (
        "CALCULATOR_HISTORY_FILE",
        "CALCULATOR_AUTOSAVE_HISTORY",
        "CALCULATOR_LOG_LEVEL",
    ):
        monkeypatch.delenv(key, raising=False)

    config = AppConfig.from_environment(dotenv_path=dotenv_file)

    assert config.history_csv_path == Path("from-dotenv.csv")
    assert config.autosave_history is False
    assert config.log_level == "WARNING"


def test_environment_values_override_dotenv_file(tmp_path, monkeypatch):
    dotenv_file = tmp_path / ".env.test"
    dotenv_file.write_text("CALCULATOR_LOG_LEVEL=DEBUG\n", encoding="utf-8")
    monkeypatch.setenv("CALCULATOR_LOG_LEVEL", "ERROR")

    config = AppConfig.from_environment(dotenv_path=dotenv_file)

    assert config.log_level == "ERROR"
