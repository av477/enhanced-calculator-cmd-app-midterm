"""Primitive arithmetic operations used by the calculator."""

from dataclasses import dataclass
from typing import Protocol

from app.calculator_config import VALID_OPERATIONS
from app.exceptions import DivisionByZeroError


class OperationStrategy(Protocol):
    """Execution interface for interchangeable arithmetic strategies."""

    def execute(self, first_number: float, second_number: float) -> float:
        """Execute the operation on two numeric operands."""


@dataclass(frozen=True)
class AdditionStrategy:
    """Apply addition to a pair of operands."""

    def execute(self, first_number: float, second_number: float) -> float:
        """Return the sum of the operands."""
        return first_number + second_number


@dataclass(frozen=True)
class SubtractionStrategy:
    """Apply subtraction to a pair of operands."""

    def execute(self, first_number: float, second_number: float) -> float:
        """Return the first operand minus the second."""
        return first_number - second_number


@dataclass(frozen=True)
class MultiplicationStrategy:
    """Apply multiplication to a pair of operands."""

    def execute(self, first_number: float, second_number: float) -> float:
        """Return the product of the operands."""
        return first_number * second_number


@dataclass(frozen=True)
class DivisionStrategy:
    """Apply division to a pair of operands."""

    def execute(self, first_number: float, second_number: float) -> float:
        """Return the first operand divided by the second."""
        if second_number == 0:
            raise DivisionByZeroError("Cannot divide by zero.")
        return first_number / second_number


@dataclass(frozen=True)
class PowerStrategy:
    """Raise the first operand to the second operand's power."""

    def execute(self, first_number: float, second_number: float) -> float:
        """Return a real-valued power result."""
        try:
            result = first_number**second_number
        except OverflowError as exc:
            raise ValueError(
                "Power result is outside the supported numeric range."
            ) from exc

        if isinstance(result, complex):
            raise ValueError("Power operation must produce a real number.")
        return result


@dataclass(frozen=True)
class RootStrategy:
    """Take the second operand's root of the first operand."""

    def execute(self, first_number: float, second_number: float) -> float:
        """Return a real-valued root result."""
        if second_number == 0:
            raise DivisionByZeroError("Cannot take a zero-degree root.")
        if first_number == 0 and second_number < 0:
            raise DivisionByZeroError("Zero cannot have a negative root degree.")

        degree = float(second_number)
        if first_number < 0:
            if not degree.is_integer() or int(degree) % 2 == 0:
                raise ValueError(
                    "A negative number requires an odd integer root degree."
                )
            return -(abs(first_number) ** (1 / degree))
        return first_number ** (1 / degree)


class OperationFactory:
    """Create the concrete strategy associated with an operation or alias."""

    _strategies: dict[str, type[OperationStrategy]] = {
        "add": AdditionStrategy,
        "subtract": SubtractionStrategy,
        "multiply": MultiplicationStrategy,
        "divide": DivisionStrategy,
        "power": PowerStrategy,
        "root": RootStrategy,
    }

    @classmethod
    def create(cls, operation: str) -> OperationStrategy:
        """Return a strategy for a supported canonical name, alias, or symbol."""
        normalized_operation = operation.strip().lower()
        canonical_operation = VALID_OPERATIONS.get(normalized_operation)
        if canonical_operation is None:
            raise ValueError(f"Invalid operation: {operation}")
        return cls._strategies[canonical_operation]()


def add(first_number: float, second_number: float) -> float:
    """Return the sum of two numbers."""
    return AdditionStrategy().execute(first_number, second_number)


def subtract(first_number: float, second_number: float) -> float:
    """Return the difference of two numbers."""
    return SubtractionStrategy().execute(first_number, second_number)


def multiply(first_number: float, second_number: float) -> float:
    """Return the product of two numbers."""
    return MultiplicationStrategy().execute(first_number, second_number)


def divide(first_number: float, second_number: float) -> float:
    """Return the quotient of two numbers."""
    return DivisionStrategy().execute(first_number, second_number)


def power(first_number: float, second_number: float) -> float:
    """Raise the first number to the power of the second number."""
    return PowerStrategy().execute(first_number, second_number)


def root(first_number: float, second_number: float) -> float:
    """Return the second-number-degree root of the first number."""
    return RootStrategy().execute(first_number, second_number)
