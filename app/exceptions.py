"""Domain-specific errors raised by the calculator."""


class InvalidOperationError(ValueError):
    """Raised when an operation name or alias is not supported."""


class InvalidNumberError(ValueError):
    """Raised when a calculator input is not a finite number."""


class InvalidExpressionError(ValueError):
    """Raised when an expression is invalid or does not produce a number."""


class DivisionByZeroError(ZeroDivisionError):
    """Raised when a division operation has a zero divisor."""

