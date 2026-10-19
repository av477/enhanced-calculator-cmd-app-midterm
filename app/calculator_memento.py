"""Immutable snapshots used to save and restore calculation history."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.calculation import Calculation


@dataclass(frozen=True)
class CalculatorMemento:
    """A point-in-time snapshot of the calculator's calculation history."""

    calculations: tuple["Calculation", ...]

