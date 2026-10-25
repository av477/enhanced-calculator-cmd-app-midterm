import io

import pytest

from app.calculation import CalculationFactory
from app.calculator import Calculator
from app.calculator_commands import (
    CalculateCommand,
    ClearHistoryCommand,
    CommandInvoker,
    CommandRegistry,
    ExitCommand,
    HelpCommand,
    HistoryCommand,
    LoadHistoryCommand,
    RedoCommand,
    SaveHistoryCommand,
    UndoCommand,
)


def test_command_invoker_queues_and_executes_calculations_in_order():
    calculator = Calculator()
    invoker = CommandInvoker()
    invoker.enqueue(CalculateCommand(calculator, 2.0, "add", 3.0))
    invoker.enqueue(CalculateCommand(calculator, 2.0, "power", 3.0))

    assert calculator.history == ()
    assert invoker.execute_all() == ("Result: 5.0", "Result: 8.0")
    assert [item.operation for item in calculator.history] == ["add", "power"]


def test_command_invoker_executes_commands_immediately():
    calculator = Calculator()
    invoker = CommandInvoker()

    assert invoker.execute(CalculateCommand(calculator, 8.0, "subtract", 3.0)) == (
        "Result: 5.0"
    )


def test_command_invoker_rejects_execution_from_an_empty_queue():
    with pytest.raises(IndexError, match="No calculator commands are queued"):
        CommandInvoker().execute_next()


def test_history_command_formats_calculations_and_empty_state():
    calculator = Calculator()
    assert HistoryCommand(calculator).execute() == "No calculations in history."

    calculator.calculate(1, "/", 3)
    assert HistoryCommand(calculator, precision=2).execute() == "1. 1.0 / 3.0 = 0.33"

    root = CalculationFactory.create_calculation(27, "root", 3)
    calculator.load_history((root,))
    assert HistoryCommand(calculator).execute() == "1. 3.0√(27.0) = 3.0"


def test_history_command_uses_ascii_root_name_for_limited_console_encoding(
    monkeypatch,
):
    class Cp1252Stream(io.StringIO):
        encoding = "cp1252"

    monkeypatch.setattr("sys.stdout", Cp1252Stream())
    calculator = Calculator()
    calculator.load_history(
        [CalculationFactory.create_calculation(27, "root", 3)]
    )

    assert HistoryCommand(calculator).execute() == "1. 3.0root(27.0) = 3.0"


def test_undo_redo_and_clear_commands_change_calculator_history():
    calculator = Calculator()
    calculator.calculate(1, "add", 2)

    assert ClearHistoryCommand(calculator).execute() == (
        "Calculation history cleared."
    )
    assert UndoCommand(calculator).execute() == "Undid the last calculation."
    assert RedoCommand(calculator).execute() == "Redid the last calculation."

    empty = Calculator()
    assert UndoCommand(empty).execute() == "Nothing to undo."
    assert RedoCommand(empty).execute() == "Nothing to redo."


def test_save_and_load_commands_round_trip_history(tmp_path):
    calculator = Calculator()
    calculator.calculate(2, "power", 3)
    file_path = tmp_path / "history.csv"

    assert SaveHistoryCommand(calculator, file_path).execute() == (
        f"History saved to {file_path}."
    )

    restored = Calculator()
    assert LoadHistoryCommand(restored, file_path, max_history_size=5).execute() == (
        f"History loaded from {file_path}."
    )
    assert restored.history[0].calculate() == 8


def test_command_registry_decorator_registers_factories_and_aliases():
    registry = CommandRegistry()

    @registry.register("exit", "quit", "Q")
    def make_exit():
        return ExitCommand()

    assert make_exit is registry._factories["exit"]
    assert registry.names == ("exit",)
    assert registry.resolve("  QUIT ") == "exit"
    assert registry.resolve("q") == "exit"
    assert isinstance(registry.create("quit"), ExitCommand)


def test_command_registry_passes_arguments_to_factories():
    registry = CommandRegistry()
    registry.register("undo")(UndoCommand)
    calculator = Calculator()

    assert registry.create("undo", calculator).execute() == "Nothing to undo."


def test_command_registry_rejects_unknown_commands():
    registry = CommandRegistry()

    assert registry.resolve("missing") is None
    with pytest.raises(KeyError, match="Unknown calculator command: missing"):
        registry.create("missing")


def test_help_command_returns_rendered_help():
    assert HelpCommand(lambda: "Commands: help").execute() == "Commands: help"


def test_exit_command_ends_session():
    command = ExitCommand()

    assert command.ends_session is True
    assert command.execute() == "Goodbye!"
