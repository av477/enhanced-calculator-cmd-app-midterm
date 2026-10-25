"""Command objects for calculator actions and their queued execution."""

from collections import deque
from collections.abc import Iterable
from pathlib import Path
import sys
from typing import Protocol

from app.calculation import Calculation
from app.calculator import Calculator
from app.history import CalculationHistory


class Command(Protocol):
    """Encapsulate one executable calculator request."""

    def execute(self) -> str:
        """Execute the request and return its user-facing result."""


class CommandInvoker:
    """Execute commands immediately or queue them for later execution."""

    def __init__(self) -> None:
        self._queue: deque[Command] = deque()

    def execute(self, command: Command) -> str:
        """Execute a command immediately."""
        return command.execute()

    def enqueue(self, command: Command) -> None:
        """Add a command to the pending execution queue."""
        self._queue.append(command)

    def execute_next(self) -> str:
        """Execute the oldest queued command."""
        if not self._queue:
            raise IndexError("No calculator commands are queued.")
        return self._queue.popleft().execute()

    def execute_all(self) -> tuple[str, ...]:
        """Execute and return results from all queued commands in order."""
        return tuple(self.execute_next() for _ in range(len(self._queue)))


class CalculateCommand:
    """Encapsulate a calculator request and its operands."""

    def __init__(
        self,
        calculator: Calculator,
        first_number: float,
        operation: str,
        second_number: float,
    ) -> None:
        self._calculator = calculator
        self._first_number = first_number
        self._operation = operation
        self._second_number = second_number

    def execute(self) -> str:
        """Run the calculation and format its result."""
        result = self._calculator.calculate(
            self._first_number,
            self._operation,
            self._second_number,
        )
        return f"Result: {result}"


class HistoryCommand:
    """Render the calculator's current history."""

    def __init__(self, calculator: Calculator, precision: int | None = None) -> None:
        self._calculator = calculator
        self._precision = precision

    def execute(self) -> str:
        """Return the formatted history contents."""
        return format_history(self._calculator.history, self._precision)


class ClearHistoryCommand:
    """Clear calculator history."""

    def __init__(self, calculator: Calculator) -> None:
        self._calculator = calculator

    def execute(self) -> str:
        """Clear history and return a confirmation."""
        self._calculator.clear_history()
        return "Calculation history cleared."


class UndoCommand:
    """Undo the latest calculator history change."""

    def __init__(self, calculator: Calculator) -> None:
        self._calculator = calculator

    def execute(self) -> str:
        """Undo a history change and report whether one was available."""
        if self._calculator.undo():
            return "Undid the last calculation."
        return "Nothing to undo."


class RedoCommand:
    """Redo the latest undone calculator history change."""

    def __init__(self, calculator: Calculator) -> None:
        self._calculator = calculator

    def execute(self) -> str:
        """Redo a history change and report whether one was available."""
        if self._calculator.redo():
            return "Redid the last calculation."
        return "Nothing to redo."


class SaveHistoryCommand:
    """Persist calculator history to a CSV file."""

    def __init__(
        self,
        calculator: Calculator,
        file_path: str | Path,
        encoding: str = "utf-8",
    ) -> None:
        self._calculator = calculator
        self._file_path = Path(file_path)
        self._encoding = encoding

    def execute(self) -> str:
        """Write the current history to its configured CSV file."""
        CalculationHistory(self._calculator.history).save_csv(
            self._file_path,
            encoding=self._encoding,
        )
        return f"History saved to {self._file_path}."


class LoadHistoryCommand:
    """Load a CSV history file into the calculator."""

    def __init__(
        self,
        calculator: Calculator,
        file_path: str | Path,
        encoding: str = "utf-8",
        max_history_size: int | None = None,
    ) -> None:
        self._calculator = calculator
        self._file_path = Path(file_path)
        self._encoding = encoding
        self._max_history_size = max_history_size

    def execute(self) -> str:
        """Load the configured CSV and replace the calculator history."""
        history = CalculationHistory.from_csv(
            self._file_path,
            encoding=self._encoding,
            max_size=self._max_history_size,
        )
        self._calculator.load_history(history.get_all())
        return f"History loaded from {self._file_path}."


def _format_calculation(
    index: int,
    calculation: Calculation,
    precision: int | None,
) -> str:
    result = calculation.calculate()
    if precision is not None:
        result = round(result, precision)
    if calculation.operation == "root":
        symbol = "√"
        try:
            symbol.encode(sys.stdout.encoding or "utf-8")
        except UnicodeEncodeError:
            symbol = "root"
        expression = f"{calculation.second_number}{symbol}({calculation.first_number})"
    else:
        expression = (
            f"{calculation.first_number} {calculation.symbol} "
            f"{calculation.second_number}"
        )
    return f"{index}. {expression} = {result}"


def format_history(
    calculations: Iterable[Calculation],
    precision: int | None = None,
) -> str:
    """Format calculations as numbered history lines."""
    items = tuple(calculations)
    if not items:
        return "No calculations in history."
    return "\n".join(
        _format_calculation(index, calculation, precision)
        for index, calculation in enumerate(items, start=1)
    )
