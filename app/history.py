"""DataFrame-backed calculation history with CSV and memento support."""

import math
from pathlib import Path
from typing import Iterable

import pandas as pd

from app.calculation import Calculation, CalculationFactory
from app.calculator_memento import CalculatorMemento


class CalculationHistory:
    """Store calculation records in a DataFrame and support state restoration."""

    COLUMNS = ("first_number", "operation", "second_number")

    def __init__(self, calculations: Iterable[Calculation] = ()) -> None:
        """Initialize history from an optional collection of calculations."""
        self._dataframe = self._dataframe_from_calculations(calculations)

    def add(self, calculation: Calculation) -> None:
        """Append a successful calculation to history."""
        row = self._dataframe_from_calculations((calculation,))
        self._dataframe = pd.concat([self._dataframe, row], ignore_index=True)

    def get_all(self) -> tuple[Calculation, ...]:
        """Reconstruct an immutable view of the stored calculations."""
        return tuple(
            Calculation(
                float(first_number), str(operation), float(second_number)
            )
            for first_number, operation, second_number in self._dataframe.itertuples(
                index=False, name=None
            )
        )

    def to_dataframe(self) -> pd.DataFrame:
        """Return a copy of the history table."""
        return self._dataframe.copy()

    def save_csv(self, file_path: str | Path) -> None:
        """Persist the history table to a CSV file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._dataframe.to_csv(path, index=False)

    @classmethod
    def from_csv(cls, file_path: str | Path) -> "CalculationHistory":
        """Load calculations from a CSV file, rejecting incomplete records."""
        dataframe = pd.read_csv(file_path, keep_default_na=False)
        missing_columns = set(cls.COLUMNS).difference(dataframe.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"History CSV is missing required columns: {missing}")
        if dataframe[list(cls.COLUMNS)].eq("").any().any():
            raise ValueError("History CSV contains empty calculation values.")

        history = cls()
        for first_number, operation, second_number in dataframe[
            list(cls.COLUMNS)
        ].itertuples(index=False, name=None):
            try:
                first_number = float(first_number)
                second_number = float(second_number)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "History CSV contains non-numeric calculation values."
                ) from exc
            if not math.isfinite(first_number) or not math.isfinite(second_number):
                raise ValueError("History CSV contains non-finite numbers.")
            try:
                calculation = CalculationFactory.create_calculation(
                    first_number, str(operation), second_number
                )
            except ValueError as exc:
                raise ValueError("History CSV contains an invalid operation.") from exc
            history.add(calculation)
        return history

    def create_memento(self) -> CalculatorMemento:
        """Capture the current history for later restoration."""
        return CalculatorMemento(self.get_all())

    def restore(self, memento: CalculatorMemento) -> None:
        """Replace the current history with a previously captured snapshot."""
        self._dataframe = self._dataframe_from_calculations(memento.calculations)

    @classmethod
    def _dataframe_from_calculations(
        cls, calculations: Iterable[Calculation]
    ) -> pd.DataFrame:
        """Build the canonical history table from calculation objects."""
        records = [
            {
                "first_number": calculation.first_number,
                "operation": calculation.operation,
                "second_number": calculation.second_number,
            }
            for calculation in calculations
        ]
        return pd.DataFrame.from_records(records, columns=cls.COLUMNS)
