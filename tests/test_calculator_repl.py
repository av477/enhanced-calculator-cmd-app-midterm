import importlib
import io
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
    ):
        monkeypatch.delenv(name, raising=False)


def test_run_interactive_handles_valid_and_invalid_operations(monkeypatch, capsys):
    responses = iter(["add", "5", "3", "divide", "10", "0", "quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    captured = capsys.readouterr()
    assert "Enhanced Calculator" in captured.out
    assert "Result: 8.0" in captured.out or "Result: 8" in captured.out
    assert "Cannot divide by zero" in captured.out


def test_run_interactive_help_history_and_exit(monkeypatch, capsys):
    responses = iter(["help", "history", "add", "4", "2", "history", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    from app.calculator_repl import run_interactive

    run_interactive()

    captured = capsys.readouterr()
    assert "Commands: help, history, clear, undo, redo, save, load, exit" in captured.out
    assert "No calculations in history." in captured.out
    assert "1. 4.0 + 2.0 = 6.0" in captured.out
    assert "Goodbye!" in captured.out


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


def test_run_interactive_handles_invalid_saved_history(monkeypatch, capsys, tmp_path):
    from app.calculator_repl import run_interactive
    from app.config import AppConfig

    history_path = tmp_path / "invalid.csv"
    history_path.write_text("wrong,columns\n1,2\n", encoding="utf-8")
    config = AppConfig(history_path, True, "INFO")

    run_interactive(config=config)

    assert "Unable to load calculator history" in capsys.readouterr().out


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


@pytest.mark.parametrize("invalid_operation", ["sqrt", "mod", ""])
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
