import importlib
import io
import logging
import runpy
import sys

import pytest

# This module tests interactive CLI behavior and the script entry points from the user's perspective.


@pytest.fixture(autouse=True)
def isolate_history_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for name in (
        "CALCULATOR_HISTORY_FILE",
        "CALCULATOR_AUTOSAVE_HISTORY",
        "CALCULATOR_LOG_LEVEL",
        "CALCULATOR_LOG_FILE",
        "CALCULATOR_LOG_DIR",
        "CALCULATOR_HISTORY_DIR",
        "CALCULATOR_MAX_HISTORY_SIZE",
        "CALCULATOR_AUTO_SAVE",
        "CALCULATOR_PRECISION",
        "CALCULATOR_MAX_INPUT_VALUE",
        "CALCULATOR_DEFAULT_ENCODING",
    ):
        monkeypatch.delenv(name, raising=False)
    yield
    from app import logger as app_logger

    if app_logger._file_handler is not None:
        logger = logging.getLogger("app.calculator")
        logger.removeHandler(app_logger._file_handler)
        app_logger._file_handler.close()
        app_logger._file_handler = None
        app_logger._file_encoding = None


def test_run_interactive_handles_valid_and_invalid_operations(
    monkeypatch, capsys, tmp_path
):
    responses = iter(["add", "5", "3", "divide", "10", "0", "quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    captured = capsys.readouterr()
    assert "Enhanced Calculator" in captured.out
    assert "Result: 8.0" in captured.out or "Result: 8" in captured.out
    assert "Cannot divide by zero" in captured.out
    assert "add" in (tmp_path / "calculator_history.csv").read_text(
        encoding="utf-8"
    )
    log_contents = (tmp_path / "calculator.log").read_text(encoding="utf-8")
    assert "add: 5.0 + 3.0 = 8.0" in log_contents
    assert "Calculation divide:" not in log_contents
    assert "WARNING Calculation failed: Cannot divide by zero." in log_contents
    assert "INFO Calculator session ended" in log_contents


def test_run_interactive_applies_configured_limits_and_directories(
    monkeypatch, capsys, tmp_path
):
    monkeypatch.setenv("CALCULATOR_LOG_DIR", "logs")
    monkeypatch.setenv("CALCULATOR_HISTORY_DIR", "history")
    monkeypatch.setenv("CALCULATOR_MAX_HISTORY_SIZE", "2")
    monkeypatch.setenv("CALCULATOR_AUTO_SAVE", "true")
    monkeypatch.setenv("CALCULATOR_PRECISION", "2")
    monkeypatch.setenv("CALCULATOR_MAX_INPUT_VALUE", "10")
    monkeypatch.setenv("CALCULATOR_DEFAULT_ENCODING", "cp1252")
    responses = iter(
        ["add", "1", "3", "divide", "1", "3", "add", "11", "1", "exit"]
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    output = capsys.readouterr().out
    assert "Result: 4.0" in output
    assert "Result: 0.33" in output
    assert "Absolute value must not exceed 10" in output
    history_file = tmp_path / "history" / "calculator_history.csv"
    log_file = tmp_path / "logs" / "calculator.log"
    assert history_file.is_file()
    assert log_file.is_file()
    assert len(history_file.read_text(encoding="cp1252").splitlines()) == 3
    assert "divide: 1.0 / 3.0 = 0.33" in log_file.read_text(
        encoding="cp1252"
    )


def test_run_interactive_help_history_and_exit(monkeypatch, capsys):
    responses = iter(["help", "history", "add", "4", "2", "history", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    captured = capsys.readouterr()
    assert "Commands: help, history, clear, undo, redo, save, load, exit" in captured.out
    assert "No calculations in history." in captured.out
    assert "1. 4.0 + 2.0 = 6.0" in captured.out
    assert "int_divide" in captured.out
    assert "percent" in captured.out
    assert "abs_diff" in captured.out
    assert "Goodbye!" in captured.out


def test_colorize_adds_requested_color_and_reset_codes():
    from colorama import Fore, Style

    from app.calculator_repl import _colorize

    assert _colorize("Result: 5", Fore.GREEN) == (
        f"{Fore.GREEN}Result: 5{Style.RESET_ALL}"
    )


def test_help_menu_decorator_includes_new_registered_operations(monkeypatch, capsys):
    from app.calculator_config import OPERATION_ALIASES
    from app.calculator_repl import _print_help

    monkeypatch.setitem(OPERATION_ALIASES, "cube", ("cube", "cub", "**"))

    _print_help()

    output = capsys.readouterr().out
    assert "cube (**)" in output
    assert "cub" in output


def test_print_history_without_precision_keeps_full_result(capsys):
    from app.calculation import CalculationFactory
    from app.calculator_commands import format_history

    calculation = CalculationFactory.create_calculation(1, "/", 3)

    print(format_history((calculation,)))

    assert "1. 1 / 3 = 0.3333333333333333" in capsys.readouterr().out


def test_run_interactive_handles_end_of_input(monkeypatch, capsys):
    def raise_eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)

    from app.calculator_repl import run_interactive

    run_interactive()

    assert "Goodbye!" in capsys.readouterr().out


def test_run_interactive_accepts_an_existing_calculator(monkeypatch, capsys):
    from app.calculator import Calculator
    from app.calculator_repl import run_interactive

    monkeypatch.setattr("builtins.input", lambda prompt="": "exit")
    run_interactive(Calculator())

    assert "Goodbye!" in capsys.readouterr().out


def test_run_interactive_handles_configuration_errors(capsys, monkeypatch):
    from app.config import ConfigurationError
    from app.calculator_repl import run_interactive

    class InvalidConfig:
        @staticmethod
        def from_environment():
            raise ConfigurationError("bad configuration")

    monkeypatch.setattr("app.calculator_repl.AppConfig", InvalidConfig)
    run_interactive()

    assert "Configuration error: bad configuration" in capsys.readouterr().out


def test_run_interactive_reports_logging_file_errors(tmp_path, capsys):
    from app.calculator import Calculator
    from app.calculator_repl import run_interactive
    from app.config import AppConfig

    blocked_directory = tmp_path / "not-a-directory"
    blocked_directory.write_text("block directory creation", encoding="utf-8")
    config = AppConfig(
        tmp_path / "history.csv",
        False,
        "INFO",
        blocked_directory / "calculator.log",
    )

    run_interactive(Calculator(), config)

    assert "Unable to configure calculator logging" in capsys.readouterr().out


def test_run_interactive_handles_invalid_saved_history(monkeypatch, capsys, tmp_path):
    from app.calculator_repl import run_interactive
    from app.config import AppConfig

    history_path = tmp_path / "invalid.csv"
    history_path.write_text("wrong,columns\n1,2\n", encoding="utf-8")
    config = AppConfig(history_path, True, "INFO")

    run_interactive(config=config)

    assert "Unable to load calculator history" in capsys.readouterr().out
    assert "ERROR Unable to load calculator history:" in (
        tmp_path / "calculator.log"
    ).read_text(encoding="utf-8")


def test_run_interactive_logs_input_and_operation_errors(monkeypatch, capsys, tmp_path):
    responses = iter(["sqrt", "add", "not-a-number", "quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    output = capsys.readouterr().out
    assert "Invalid operation" in output
    assert "Please enter a valid number" in output
    log_contents = (tmp_path / "calculator.log").read_text(encoding="utf-8")
    assert "WARNING Operation failed: Invalid operation" in log_contents
    assert "WARNING Input validation failed:" in log_contents


def test_run_interactive_logs_unexpected_value_errors(monkeypatch, capsys, tmp_path):
    from app.calculator import Calculator
    from app.calculator_repl import run_interactive

    def fail_calculation(*_args):
        raise ValueError("unexpected calculation error")

    calculator = Calculator()
    monkeypatch.setattr(calculator, "calculate", fail_calculation)
    responses = iter(["add", "1", "2", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    run_interactive(calculator=calculator)

    assert "Error: unexpected calculation error" in capsys.readouterr().out
    log_contents = (tmp_path / "calculator.log").read_text(encoding="utf-8")
    assert "ERROR Calculation or command failed: unexpected calculation error" in (
        log_contents
    )


def test_run_interactive_logs_filesystem_errors(monkeypatch, capsys, tmp_path):
    from app.calculator_repl import run_interactive
    from app.history import CalculationHistory

    def fail_save(*_args, **_kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr(CalculationHistory, "save_csv", fail_save)
    responses = iter(["save", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    run_interactive()

    assert "History file error: disk unavailable" in capsys.readouterr().out
    log_contents = (tmp_path / "calculator.log").read_text(encoding="utf-8")
    assert "ERROR History file operation failed: disk unavailable" in log_contents


def test_run_interactive_can_disable_csv_autosaving(monkeypatch, capsys, tmp_path):
    from app.calculator_repl import run_interactive
    from app.config import AppConfig

    history_path = tmp_path / "disabled.csv"
    config = AppConfig(history_path, False, "INFO")
    responses = iter(["add", "2", "3", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    run_interactive(config=config)

    assert "Result: 5.0" in capsys.readouterr().out
    assert not history_path.exists()


@pytest.mark.parametrize("invalid_operation", ["sqrt", "foobar", ""])
def test_run_interactive_invalid_operation_shows_available_choices(
    monkeypatch, capsys, invalid_operation
):
    responses = iter([invalid_operation, "quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    captured = capsys.readouterr()
    assert "Invalid operation" in captured.out
    assert "add (+)" in captured.out
    assert "subtract (-)" in captured.out
    assert "multiply (*)" in captured.out
    assert "divide (/)" in captured.out
    assert "power (^)" in captured.out
    assert "root (" in captured.out


def test_root_symbol_falls_back_for_non_unicode_consoles(monkeypatch):
    from app.calculator_repl import _display_symbol

    class Cp1252Stream(io.StringIO):
        encoding = "cp1252"

    monkeypatch.setattr("app.calculator_repl.sys.stdout", Cp1252Stream())

    assert _display_symbol("root") == "root"
    assert _display_symbol("add") == "+"


def test_run_interactive_power_and_root_show_results_and_history(monkeypatch, capsys):
    responses = iter(["power", "2", "3", "root", "27", "3", "history", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    output = capsys.readouterr().out
    assert "Result: 8" in output
    assert "Result: 3.0" in output
    assert "1. 2.0 ^ 3.0 = 8" in output
    assert "2. 3.0√(27.0) = 3.0" in output


@pytest.mark.parametrize(
    ("operation", "first_number", "second_number", "expected"),
    [
        ("mod", "17", "5", "Result: 2.0"),
        ("int_divide", "-17", "5", "Result: -3.0"),
        ("percent", "12", "30", "Result: 40.0"),
        ("abs_diff", "4", "10", "Result: 6.0"),
    ],
)
def test_run_interactive_supports_additional_operations(
    monkeypatch, capsys, operation, first_number, second_number, expected
):
    responses = iter([operation, first_number, second_number, "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    assert expected in capsys.readouterr().out


def test_run_interactive_invalid_root_does_not_add_history(monkeypatch, capsys):
    responses = iter(["root", "-16", "2", "history", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    output = capsys.readouterr().out
    assert "odd integer root degree" in output
    assert "No calculations in history." in output


def test_run_interactive_undo_and_redo_commands(monkeypatch, capsys):
    responses = iter(
        ["add", "4", "2", "undo", "history", "redo", "history", "exit"]
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    output = capsys.readouterr().out
    assert "Undid the last calculation." in output
    assert "Redid the last calculation." in output
    assert "No calculations in history." in output
    assert "1. 4.0 + 2.0 = 6.0" in output


def test_run_interactive_clear_save_and_load_commands(monkeypatch, capsys, tmp_path):
    from app.calculator import Calculator
    from app.config import AppConfig
    from app.calculator_repl import run_interactive

    history_path = tmp_path / "saved.csv"
    calculator = Calculator()
    config = AppConfig(history_path, False, "INFO")
    responses = iter(
        ["add", "2", "3", "save", "clear", "history", "load", "history", "exit"]
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    run_interactive(calculator, config)

    output = capsys.readouterr().out
    assert "History saved to" in output
    assert "Calculation history cleared." in output
    assert "No calculations in history." in output
    assert "History loaded from" in output
    assert "1. 2.0 + 3.0 = 5.0" in output


def test_run_interactive_reports_missing_file_on_load_and_continues(
    monkeypatch, capsys, tmp_path
):
    from app.calculator import Calculator
    from app.config import AppConfig
    from app.calculator_repl import run_interactive

    config = AppConfig(tmp_path / "missing.csv", False, "INFO")
    responses = iter(["load", "history", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    run_interactive(Calculator(), config)

    output = capsys.readouterr().out
    assert "History file error" in output
    assert "No calculations in history." in output
    assert "Goodbye!" in output


def test_run_interactive_reports_invalid_csv_data_and_continues(
    monkeypatch, capsys, tmp_path
):
    from app.calculator import Calculator
    from app.config import AppConfig
    from app.calculator_repl import run_interactive

    history_file = tmp_path / "invalid.csv"
    history_file.write_text("", encoding="utf-8")
    config = AppConfig(history_file, False, "INFO")
    responses = iter(["load", "history", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    run_interactive(Calculator(), config)

    output = capsys.readouterr().out
    assert "History data error: Unable to read calculator history" in output
    assert "No calculations in history." in output
    assert "Goodbye!" in output


def test_run_interactive_loads_existing_history_and_appends_to_csv(
    monkeypatch, capsys, tmp_path
):
    from app.calculation import CalculationFactory
    from app.history import CalculationHistory

    path = tmp_path / "calculator_history.csv"
    CalculationHistory(
        [CalculationFactory.create_calculation(2, "^", 3)]
    ).save_csv(path)
    responses = iter(["history", "add", "4", "5", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    output = capsys.readouterr().out
    assert "1. 2.0 ^ 3.0 = 8" in output
    assert "Result: 9.0" in output
    loaded = CalculationHistory.from_csv(path).get_all()
    assert [(item.first_number, item.operation) for item in loaded] == [
        (2, "power"),
        (4, "add"),
    ]


def test_run_interactive_rejects_non_finite_numbers(monkeypatch, capsys):
    responses = iter(["add", "nan", "5", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    captured = capsys.readouterr()
    assert "Please enter a finite number" in captured.out


def test_run_interactive_invalid_number_prompts_user_again(monkeypatch, capsys):
    responses = iter(["add", "abc", "5", "quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    captured = capsys.readouterr()
    assert "Invalid first number" in captured.out
    assert "Please enter a valid number" in captured.out


def test_cli_module_runs_main(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt="": "quit")
    sys.modules.pop("app.calculator_repl", None)
    runpy.run_module("app.calculator_repl", run_name="__main__")

    captured = capsys.readouterr()
    assert "Enhanced Calculator" in captured.out
    assert "Goodbye!" in captured.out


def test_cli_module_import_does_not_run_interactive(capsys):
    sys.modules.pop("app.calculator_repl", None)
    cli_module = importlib.import_module("app.calculator_repl")

    assert callable(cli_module.run_interactive)
    assert capsys.readouterr().out == ""


def test_calculator_repl_module_runs_main(monkeypatch, capsys):
    responses = iter(["quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    sys.modules.pop("app.calculator_repl", None)
    runpy.run_module("app.calculator_repl", run_name="__main__")

    captured = capsys.readouterr()
    assert "Enhanced Calculator" in captured.out
    assert "Goodbye!" in captured.out
