import logging

import pytest

from app.calculation import CalculationFactory
from app.calculator import Calculator
from app.calculator_observers import AutoSaveHistoryObserver, LoggingObserver
from app.history import CalculationHistory
from app.operations import (
    AdditionStrategy,
    AbsoluteDifferenceStrategy,
    DivisionStrategy,
    IntegerDivisionStrategy,
    ModulusStrategy,
    OperationFactory,
    PercentageStrategy,
    PowerStrategy,
    RootStrategy,
)
from app import logger as app_logger


def test_calculator_facade_executes_and_tracks_successful_calculations():
    calculator = Calculator()

    assert calculator.calculate(2, "+", 3) == 5
    assert len(calculator.history) == 1
    assert calculator.history[0].operation == "add"


def test_failed_calculation_does_not_change_history_or_undo_state():
    calculator = Calculator()

    with pytest.raises(ZeroDivisionError):
        calculator.calculate(2, "divide", 0)

    assert calculator.history == ()
    assert calculator.undo() is False


def test_undo_redo_restore_history_and_new_calculation_discards_redo():
    calculator = Calculator()
    calculator.calculate(2, "+", 3)
    calculator.calculate(4, "*", 5)

    assert calculator.undo() is True
    assert [item.operation for item in calculator.history] == ["add"]
    assert calculator.redo() is True
    assert [item.operation for item in calculator.history] == ["add", "multiply"]

    assert calculator.undo() is True
    calculator.calculate(8, "-", 1)
    assert calculator.redo() is False
    assert [item.operation for item in calculator.history] == ["add", "subtract"]


def test_multiple_undo_redo_steps_restore_each_history_snapshot():
    calculator = Calculator()
    calculator.calculate(2, "+", 3)
    calculator.calculate(4, "*", 5)
    calculator.calculate(9, "-", 1)

    assert calculator.undo() is True
    assert [item.operation for item in calculator.history] == ["add", "multiply"]
    assert calculator.undo() is True
    assert [item.operation for item in calculator.history] == ["add"]
    assert calculator.undo() is True
    assert calculator.history == ()
    assert calculator.undo() is False

    assert calculator.redo() is True
    assert [item.operation for item in calculator.history] == ["add"]
    assert calculator.redo() is True
    assert [item.operation for item in calculator.history] == ["add", "multiply"]
    assert calculator.redo() is True
    assert [item.operation for item in calculator.history] == [
        "add",
        "multiply",
        "subtract",
    ]
    assert calculator.redo() is False


def test_calculator_applies_history_limit_and_result_precision():
    calculator = Calculator(max_history_size=2, precision=2)

    assert calculator.calculate(1, "/", 3) == 0.33
    calculator.calculate(2, "+", 3)
    calculator.calculate(4, "+", 5)

    assert [item.first_number for item in calculator.history] == [2, 4]


def test_clear_history_can_be_undone_and_redone():
    calculator = Calculator()
    calculator.calculate(2, "+", 3)

    calculator.clear_history()
    assert calculator.history == ()
    assert calculator.undo() is True
    assert len(calculator.history) == 1
    assert calculator.redo() is True
    assert calculator.history == ()


def test_load_history_replaces_state_and_clears_undo_redo():
    calculator = Calculator()
    calculator.calculate(2, "+", 3)
    replacement = CalculationFactory.create_calculation(9, "^", 2)

    calculator.load_history((replacement,))

    assert calculator.history == (replacement,)
    assert calculator.undo() is False
    assert calculator.redo() is False


def test_observers_receive_calculation_undo_and_redo_events():
    class RecordingObserver:
        def __init__(self):
            self.actions = []

        def update(self, event):
            self.actions.append((event.action, len(event.history)))

    observer = RecordingObserver()
    calculator = Calculator(observers=(observer,))
    calculator.calculate(3, "^", 2)
    calculator.undo()
    calculator.redo()

    assert observer.actions == [("calculate", 1), ("undo", 0), ("redo", 1)]


def test_observer_receives_clear_and_load_events():
    class RecordingObserver:
        def __init__(self):
            self.actions = []

        def update(self, event):
            self.actions.append(event.action)

    observer = RecordingObserver()
    calculator = Calculator(observers=(observer,))
    calculation = CalculationFactory.create_calculation(3, "+", 4)
    calculator.calculate(3, "+", 4)
    calculator.clear_history()
    calculator.load_history((calculation,))

    assert observer.actions == ["calculate", "clear", "load"]


def test_observers_can_be_added_and_removed():
    class RecordingObserver:
        def __init__(self):
            self.events = 0

        def update(self, event):
            self.events += 1

    observer = RecordingObserver()
    calculator = Calculator()
    calculator.add_observer(observer)
    calculator.add_observer(observer)
    calculator.calculate(1, "add", 1)
    calculator.remove_observer(observer)
    calculator.calculate(2, "add", 2)

    assert observer.events == 1


def test_logging_observer_logs_calculation(caplog):
    calculator = Calculator(observers=(LoggingObserver(),))

    with caplog.at_level(logging.INFO, logger="app.calculator"):
        calculator.calculate(3, "*", 4)

    assert "Calculation multiply: 3 * 4 = 12" in caplog.text


@pytest.mark.parametrize(
    ("operation", "first_number", "second_number"),
    [
        ("power", 2, 3),
        ("root", 27, 3),
        ("modulus", 10, 3),
        ("integer_division", 10, 3),
        ("percentage", 25, 100),
        ("absolute_difference", 10, 3),
    ],
)
def test_logging_observer_logs_each_additional_operation(
    caplog, operation, first_number, second_number
):
    calculator = Calculator(observers=(LoggingObserver(),))

    with caplog.at_level(logging.INFO, logger="app.calculator"):
        calculator.calculate(first_number, operation, second_number)

    assert f"Calculation {operation}:" in caplog.text


def test_logging_observer_writes_calculation_details_to_file(tmp_path):
    log_file = tmp_path / "calculator.log"
    app_logger.configure_logging("INFO", log_file)
    try:
        first_handler = app_logger._file_handler
        app_logger.configure_logging("DEBUG", log_file)
        assert app_logger._file_handler is first_handler

        replacement_log_file = tmp_path / "replacement.log"
        app_logger.configure_logging("INFO", replacement_log_file)
        assert app_logger._file_handler is not first_handler

        Calculator(observers=(LoggingObserver(),)).calculate(3, "*", 4)

        assert first_handler is not None
        assert first_handler.stream is None
        log_contents = replacement_log_file.read_text(encoding="utf-8")
        assert "multiply: 3 * 4 = 12" in log_contents
    finally:
        logger = logging.getLogger("app.calculator")
        if app_logger._file_handler is not None:
            logger.removeHandler(app_logger._file_handler)
            app_logger._file_handler.close()
            app_logger._file_handler = None
            app_logger._file_encoding = None


def test_autosave_observer_writes_calculations_and_tracks_undo_redo(tmp_path):
    history_file = tmp_path / "history.csv"
    calculator = Calculator(observers=(AutoSaveHistoryObserver(history_file),))
    calculator.calculate(2, "^", 3)
    records = CalculationHistory.from_csv(history_file).get_all()
    assert [(item.first_number, item.operation, item.second_number) for item in records] == [
        (2, "power", 3)
    ]

    calculator.undo()
    assert CalculationHistory.from_csv(history_file).get_all() == ()
    calculator.redo()
    assert CalculationHistory.from_csv(history_file).get_all() == records


@pytest.mark.parametrize(
    ("operation", "strategy_type"),
    [
        ("+", AdditionStrategy),
        ("/", DivisionStrategy),
        ("pow", PowerStrategy),
        ("√", RootStrategy),
        ("%", ModulusStrategy),
        ("//", IntegerDivisionStrategy),
        ("pct", PercentageStrategy),
        ("abs", AbsoluteDifferenceStrategy),
    ],
)
def test_operation_factory_creates_strategies_from_names_aliases_and_symbols(
    operation, strategy_type
):
    assert isinstance(OperationFactory.create(operation), strategy_type)


def test_operation_factory_rejects_unsupported_operations():
    with pytest.raises(ValueError, match="Invalid operation"):
        OperationFactory.create("sqrt")
