"""Domain-specific errors raised by the calculator."""


class OperationError(ValueError):
    """Raised when an operation cannot be performed."""


class ValidationError(ValueError):
    """Raised when user-provided input fails validation."""


class HistoryDataError(ValueError):
    """Raised when a history CSV contains invalid or unreadable data."""


class HistoryFileError(OSError):
    """Raised when a history CSV cannot be read or written."""


class InvalidOperationError(OperationError):
    """Raised when an operation name or alias is not supported."""


class InvalidNumberError(ValidationError):
    """Raised when a calculator input is not a finite number."""


class InvalidExpressionError(ValidationError):
    """Raised when an expression is invalid or does not produce a number."""


class DivisionByZeroError(ZeroDivisionError):
    """Raised when a division operation has a zero divisor."""
