import pytest

from app.exceptions import (
    DivisionByZeroError,
    HistoryDataError,
    HistoryFileError,
    InvalidExpressionError,
    InvalidNumberError,
    InvalidOperationError,
    OperationError,
    ValidationError,
)


@pytest.mark.parametrize(
    ("exception_type", "base_type", "message"),
    [
        (InvalidOperationError, ValueError, "Unsupported operation"),
        (InvalidNumberError, ValueError, "Invalid number"),
        (InvalidExpressionError, ValueError, "Malformed expression"),
        (DivisionByZeroError, ZeroDivisionError, "Cannot divide by zero"),
        (OperationError, ValueError, "Operation failed"),
        (ValidationError, ValueError, "Invalid input"),
        (HistoryDataError, ValueError, "Invalid CSV"),
        (HistoryFileError, OSError, "Cannot save CSV"),
    ],
)
def test_calculator_exceptions_preserve_messages_and_standard_bases(
    exception_type, base_type, message
):
    exception = exception_type(message)

    assert isinstance(exception, base_type)
    assert str(exception) == message


def test_specific_exceptions_extend_their_category_errors():
    assert isinstance(InvalidOperationError("bad operation"), OperationError)
    assert isinstance(InvalidNumberError("bad number"), ValidationError)
    assert isinstance(InvalidExpressionError("bad expression"), ValidationError)
