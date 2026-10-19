"""Calculation objects and calculation helpers."""

from dataclasses import dataclass

from app.calculator_config import (
    INVALID_OPERATION_MESSAGE,
    OPERATION_SYMBOLS,
    VALID_OPERATIONS,
)
from app.exceptions import InvalidExpressionError, InvalidOperationError
from app.operations import OperationFactory


@dataclass(frozen=True)
class Calculation:
    """Immutable calculation request using a canonical operation name."""

    first_number: float
    operation: str
    second_number: float

    def calculate(self) -> float:
        """Execute the stored operation and return its numeric result."""
        strategy = OperationFactory.create(self.operation)
        return strategy.execute(self.first_number, self.second_number)

    @property
    def symbol(self) -> str:
        """Return the arithmetic symbol for this calculation."""
        return OPERATION_SYMBOLS[self.operation]


class CalculationFactory:
    """Create calculations from operation names, aliases, or symbols."""

    @staticmethod
    def create_calculation(
        first_number: float,
        operation: str,
        second_number: float,
    ) -> Calculation:
        """Normalize an operation alias and construct a calculation."""
        normalized_operation = operation.strip().lower()
        if normalized_operation not in VALID_OPERATIONS:
            raise InvalidOperationError(INVALID_OPERATION_MESSAGE)

        canonical_operation = VALID_OPERATIONS[normalized_operation]
        return Calculation(first_number, canonical_operation, second_number)


def calculate(first_number: float, operation: str, second_number: float) -> float:
    """Perform a calculation using a canonical name, alias, or symbol."""
    calculation = CalculationFactory.create_calculation(
        first_number, operation, second_number
    )
    return calculation.calculate()


def evaluate_expression(expression: str) -> float:
    """Evaluate a mathematical expression and return its result as a float."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
    except Exception as exc:
        raise InvalidExpressionError(f"Invalid expression: {expression}") from exc

    if isinstance(result, (int, float)):
        return float(result)

    raise InvalidExpressionError(
        f"Expression did not produce a number: {expression}"
    )
