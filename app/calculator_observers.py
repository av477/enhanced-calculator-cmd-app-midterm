"""Observer interfaces and built-in calculation event observers."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.calculation import Calculation
from app.history import CalculationHistory
from app.logger import get_logger


@dataclass(frozen=True)
class CalculationEvent:
    """A calculator state change published to registered observers."""

    action: str
    history: tuple[Calculation, ...]
    calculation: Calculation | None = None
    result: float | None = None


class CalculationObserver(Protocol):
    """Receives calculator state change notifications."""

    def update(self, event: CalculationEvent) -> None:
        """React to a calculation or history state change."""


class LoggingObserver:
    """Log calculation, undo, and redo events through Python logging."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or get_logger()

    def update(self, event: CalculationEvent) -> None:
        if event.calculation is not None:
            self._logger.info(
                "Calculation %s: %s %s %s = %s",
                event.calculation.operation,
                event.calculation.first_number,
                event.calculation.symbol,
                event.calculation.second_number,
                event.result,
            )
        else:
            self._logger.info(
                "Calculator history action: %s (%d entries)",
                event.action,
                len(event.history),
            )


class AutoSaveObserver:
    """Persist the latest calculation history as CSV after every state change."""

    def __init__(self, file_path: str | Path, encoding: str = "utf-8") -> None:
        self._file_path = Path(file_path)
        self._encoding = encoding

    def update(self, event: CalculationEvent) -> None:
        CalculationHistory(event.history).save_csv(
            self._file_path,
            encoding=self._encoding,
        )


AutoSaveHistoryObserver = AutoSaveObserver
