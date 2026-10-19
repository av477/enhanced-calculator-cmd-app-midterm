import pytest

from app.exceptions import (
    DivisionByZeroError,
    InvalidExpressionError,
    InvalidNumberError,
    InvalidOperationError,
)


@pytest.mark.parametrize(
    ("exception_type", "base_type", "message"),
    [
        (InvalidOperationError, ValueError, "Unsupported operation"),
        (InvalidNumberError, ValueError, "Invalid number"),
        (InvalidExpressionError, ValueError, "Malformed expression"),
        (DivisionByZeroError, ZeroDivisionError, "Cannot divide by zero"),
    ],
)
def test_calculator_exceptions_preserve_messages_and_standard_bases(
    exception_type, base_type, message
):
    exception = exception_type(message)

    assert isinstance(exception, base_type)
    assert str(exception) == message
