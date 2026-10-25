"""DataFrame-backed calculation history with CSV and memento support."""

import math
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from app.calculation import Calculation, CalculationFactory
from app.calculator_memento import CalculatorMemento
from app.exceptions import HistoryDataError, HistoryFileError


class CalculationHistory:
    """Store calculation records in a DataFrame and support state restoration."""

    COLUMNS = (
        "operation",
        "first_number",
        "second_number",
        "result",
        "timestamp",
    )
    REQUIRED_COLUMNS = ("first_number", "operation", "second_number")

    def __init__(
        self,
        calculations: Iterable[Calculation] = (),
        max_size: int | None = None,
    ) -> None:
        """Initialize history from an optional collection of calculations."""
        self._validate_max_size(max_size)
        self._max_size = max_size
        self._dataframe = self._dataframe_from_calculations(calculations)
        self._trim_to_max_size()

    def add(self, calculation: Calculation) -> None:
        """Append a successful calculation to history."""
        row = self._dataframe_from_calculations((calculation,))
        self._dataframe = pd.concat([self._dataframe, row], ignore_index=True)
        self._trim_to_max_size()

    def get_all(self) -> tuple[Calculation, ...]:
        """Reconstruct an immutable view of the stored calculations."""
        return tuple(
            Calculation(
                float(first_number),
                str(operation),
                float(second_number),
                datetime.fromisoformat(str(timestamp)),
            )
            for first_number, operation, second_number, timestamp in self._dataframe[
                ["first_number", "operation", "second_number", "timestamp"]
            ].itertuples(
                index=False, name=None
            )
        )

    def to_dataframe(self) -> pd.DataFrame:
        """Return a copy of the history table."""
        return self._dataframe.copy()

    def save_csv(self, file_path: str | Path, encoding: str = "utf-8") -> None:
        """Persist the history table to a CSV file."""
        path = Path(file_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._dataframe.to_csv(path, index=False, encoding=encoding)
        except (OSError, UnicodeError, LookupError) as exc:
            raise HistoryFileError(
                f"Unable to save calculator history to {path}: {exc}"
            ) from exc

    @classmethod
    def from_csv(
        cls,
        file_path: str | Path,
        encoding: str = "utf-8",
        max_size: int | None = None,
    ) -> "CalculationHistory":
        """Load calculations from a CSV file, rejecting incomplete records."""
        path = Path(file_path)
        try:
            dataframe = pd.read_csv(
                path,
                keep_default_na=False,
                encoding=encoding,
            )
        except OSError as exc:
            raise HistoryFileError(
                f"Unable to read calculator history from {path}: {exc}"
            ) from exc
        except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
            raise HistoryDataError(
                f"Unable to read calculator history from {path}: {exc}"
            ) from exc
        except UnicodeError as exc:
            raise HistoryDataError(
                f"Unable to decode calculator history at {path} "
                f"using {encoding}: {exc}"
            ) from exc
        missing_columns = set(cls.REQUIRED_COLUMNS).difference(dataframe.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise HistoryDataError(
                f"History CSV is missing required columns: {missing}"
            )
        required_values = dataframe[list(cls.REQUIRED_COLUMNS)]
        if required_values.eq("").any().any():
            raise HistoryDataError("History CSV contains empty calculation values.")

        has_result = "result" in dataframe.columns
        has_timestamp = "timestamp" in dataframe.columns
        if has_timestamp and dataframe["timestamp"].eq("").any():
            raise HistoryDataError("History CSV contains empty timestamps.")

        history = cls(max_size=max_size)
        for row in dataframe.to_dict(orient="records"):
            try:
                first_number = float(row["first_number"])
                second_number = float(row["second_number"])
            except (TypeError, ValueError) as exc:
                raise HistoryDataError(
                    "History CSV contains non-numeric calculation values."
                ) from exc
            if not math.isfinite(first_number) or not math.isfinite(second_number):
                raise HistoryDataError("History CSV contains non-finite numbers.")

            if has_result:
                try:
                    result = float(row["result"])
                except (TypeError, ValueError) as exc:
                    raise HistoryDataError(
                        "History CSV contains a non-numeric result."
                    ) from exc
                if not math.isfinite(result):
                    raise HistoryDataError(
                        "History CSV contains a non-finite result."
                    )

            timestamp = None
            if has_timestamp:
                try:
                    timestamp = datetime.fromisoformat(str(row["timestamp"]))
                except (TypeError, ValueError) as exc:
                    raise HistoryDataError(
                        "History CSV contains an invalid timestamp."
                    ) from exc
            try:
                calculation = CalculationFactory.create_calculation(
                    first_number, str(row["operation"]), second_number
                )
            except ValueError as exc:
                raise HistoryDataError(
                    "History CSV contains an invalid operation."
                ) from exc
            try:
                calculated_result = calculation.calculate()
            except (ArithmeticError, ValueError) as exc:
                raise HistoryDataError(
                    "History CSV contains a calculation that cannot be evaluated."
                ) from exc
            if has_result and not math.isclose(result, calculated_result):
                raise HistoryDataError(
                    "History CSV contains a result that does not match its operands."
                )
            if timestamp is not None:
                calculation = Calculation(
                    calculation.first_number,
                    calculation.operation,
                    calculation.second_number,
                    timestamp,
                )
            history.add(calculation)
        return history

    def create_memento(self) -> CalculatorMemento:
        """Capture the current history for later restoration."""
        return CalculatorMemento(self.get_all())

    def restore(self, memento: CalculatorMemento) -> None:
        """Replace the current history with a previously captured snapshot."""
        self._dataframe = self._dataframe_from_calculations(memento.calculations)
        self._trim_to_max_size()

    def _trim_to_max_size(self) -> None:
        """Discard oldest records when history exceeds its configured limit."""
        if self._max_size is not None and len(self._dataframe) > self._max_size:
            self._dataframe = self._dataframe.tail(self._max_size).reset_index(
                drop=True
            )

    @staticmethod
    def _validate_max_size(max_size: int | None) -> None:
        if max_size is not None and (
            isinstance(max_size, bool)
            or not isinstance(max_size, int)
            or max_size < 1
        ):
            raise ValueError("max_size must be a positive integer.")

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
                "result": calculation.calculate(),
                "timestamp": calculation.timestamp.isoformat(),
            }
            for calculation in calculations
        ]
        return pd.DataFrame.from_records(records, columns=cls.COLUMNS)
